"""Usage: snapshot.py url
"""

# Resources
# ---------
# RFC1808 - Relative Uniform Resource Locators

# RFC2616 - Hypertext Transfer Protocol -- HTTP/1.1
#   14.14 Content-Location

# HTML 4.01 Specification (http://www.w3.org/TR/html401)
#   12 - Links
#   14 - Style Sheets 

# CSS2 Specification (http://www.w3.org/TR/REC-CSS2)


# Design discussion
# 
# Snapshot of what's in the browser v.s. fetch again
# - only browser knows what showing
# - fetch again may get different content. (cookie, authentication, Javascript)
# - may trigger a transaction (though GET should be idempotent)
# - counterpoint bookmark is used to refetch.
# - use proxy to cache. Complication, browser also have cache, not all content showing are fetched via proxy
# - drive browser to refetch? Borwser will use right cookie and authentication. Clever but tricky.
# - IE refetch.


import logging
import re
import sets
import StringIO
import sys
import urllib2
import urlparse

from cssutils.cssparser import *
from minds.util import html_pull_parser as hpp
from minds.util import httputil

log = logging.getLogger('snapshot')

APPLICATION = 'application/octet-stream'
TEXT_HTML = 'text/html'
TEXT_CSS = 'text/css'

# links is list of (tag, baseuri, uri, content-type)


# ----------------------------------------------------------------------
# HTML Parsing

LINKABLE_TAGS = {
  'area':   'href',        
  'body':   'background',  
  'frame':  'src',         
  'iframe': 'src',         
  'img':    'src',         
  'input':  'src',         
  'link':   'href',        
  'script': 'src',         
}

# Below are attributes that are defined by W3C but are obscure or have
# little browser support. They are not supported here because of 
# difficulty of testing.
#    BLOCKQUOTE, Q   cite      
#    DEL, INS        cite      
#    HEAD            profile   
#    IMG             longdesc  
#    FRAME, IFRAME   longdesc  
#    IMG, INPUT      usemap    

# Tags below are not supported
#    OBJECT
#    APPLET

# <a> and <form> also have URI attributes but will not be snapshoot.


def scan_html(fp, baseuri, append):

    token_stream = hpp.generate_tokens(fp, comment=True)
    for token in token_stream:
        if token[0] != hpp.TAG:
            continue
        tag = token[1]

        # ----------------------------------------------------------------------
        # handle <style> block
        if tag == 'style':
            # HACK: <style> should only be valid inside <head>
            styles = []
            for token in token_stream:
                if token[0] == hpp.DATA:
                    styles.append(token[1])    
                elif token[0] == hpp.COMMENT:   
                    styles.append(token[1])     # CSS enclosed by HTML comment!
                elif token[0] == hpp.TAG:
                    if token[1] == 'style':
                        # <style> follows by <style>??? OK, treat it as <style>. 
                        continue
                    else:
                        # No </style>??? Any other open tags would close <style>
                        break
                elif token[0] == hpp.ENDTAG:
                    break
            else:
                # the stream is exhausted? Make sure next step knows 
                # there is no unprocessed token.
                token = None        
                    
            # process the style content
            _scan_html_style(tag, ''.join(styles), baseuri, append)
                    
            # look at last unprecessed token
            if not token:
                # TODO: test
                break
            elif token[0] == hpp.ENDTAG:
                # hopefully this ends with a valid </style>
                # TODO: test
                continue
            else:    
                # we got a (non-style) begin TAG??? OK, we'll process this tag.
                tag = token[1]
                # TODO: test
                
        # ----------------------------------------------------------------------
        # read TAG and its attributes
        isLinkTag = (tag == 'link')
        uri_attr = LINKABLE_TAGS.get(tag,'')
                    
        # run through attribute list to find relevant info
        uri = style = rel = ctype = ''
        for n, v in token[2]:               # TODO: need to XML decode?
            if n == uri_attr:
                uri = v
            elif n == 'style':
                style = v    
            elif isLinkTag:
                if n == 'rel':
                    rel = v
                elif n == 'type':
                    ctype = v

        # ----------------------------------------------------------------------
        # handle style attribute
        if style:
            _scan_html_style(tag, style, baseuri, append)

        # ----------------------------------------------------------------------
        # handle uri attributes (href, src, etc)
        if not uri:
            continue     
        #print >>sys.stderr, tag, uri, ctype
        
        # note: the ctype is advisory, content-type from http may not be consistent
        # everything not HTML or CSS is APPLICATION
        if tag in ['frame','iframe']:
            ctype = TEXT_HTML
        elif isLinkTag:
            if rel.lower() == 'stylesheet': # TODO: rel="alternate stylesheet"?
                ctype = TEXT_CSS
            elif ctype != TEXT_CSS:
                # only want CSS from <link>
                continue
        else:
            ctype = APPLICATION        

        append(baseuri, uri, ctype, tag)


def _scan_html_style(tag, style, baseuri, append):
    """ 
    Handles inline CSS in HTML within a style block or in the style attribute. 
    """
    # quick test to find if anything of our interest 
    # (note: keyword is case-sensitive)
    if style.find('url(') < 0 and style.find('@import') < 0:
        return
    fp = StringIO.StringIO(style)    
    scan_css(fp, baseuri, append, tag)


# ----------------------------------------------------------------------
# CSS Parsing

# See CSS2 4.3.4 URL + URN = URI for syntax rule 
#   http://www.w3.org/TR/REC-CSS2/syndata.html#uri

# e.g. - url( "yellow" ) -> "yellow"
url_pattern = re.compile(ur"url\( \s* (.+?) \s* \)", re.VERBOSE)

# HACK: this simple parser is not foolproof. It does not handle mismatched 
# quotes and escapes inside quote.

def _get_url(s):
    """ extract the %uri% attribute """
    m = url_pattern.search(s)
    if not m:
        return None
    url = m.group(1)
    if len(url) >= 2:
        if (url[0] == "'" and url[-1] == "'") or \
           (url[0] == '"' and url[-1] == '"'):
            # strip quotes
            url = url[1:-1]
    return url


LINKABLE_PROPERTIES = [
    'background-image',
    'content',
    'cue-after',
    'cue-before',
    'cursor',
    'list-style-image',
    'play-during',
]

LINKABLE_SHORTHAND_PROPERTIES = [
    'background',
    'cue',
    'list-style',
]

def scan_css(fp, baseuri, append, prefix=''):
    """ scan a CSS for all its external links """
    
    # prefix is the HTML tag that has inline CSS
    if prefix: 
        prefix += ' '
        
    cp = CSSParser()
    stylesheet = cp.parseString(fp.read().decode('UTF-8'))               ##HACK encoding
    for rule in stylesheet.cssRules:                # rule: CSSRule
        if rule.type == rule.STYLE_RULE:            # CSSStyleRule
            #print rule.type, rule.selectorText
            style = rule.style                      # CSSStyleDeclaration
            for i in range(style.length):
                property = style.item(i)
                pvalue = style.getPropertyValue(property)
                if property in LINKABLE_PROPERTIES:
                    url = _get_url(pvalue)
                    if url:
                        append(baseuri, url, APPLICATION, prefix + property)
                elif property in LINKABLE_SHORTHAND_PROPERTIES:
                    # HACK: we are taking shortcut here. Match the URL 
                    # attribute without regard to its position in the list.
                    url = _get_url(pvalue)
                    if url:
                        append(baseuri, url, APPLICATION, prefix + property)

        elif rule.type == rule.IMPORT_RULE:         # CSSImportRule
            if rule.href:
                append(baseuri, rule.href, TEXT_CSS, prefix + '@import')


# ----------------------------------------------------------------------
# Fetcher

class Resource(object):
    """ Represents a resource fetched. """
    def __init__(self, parent, uri='', ctype='', tag=''):
        self.parent = parent
        self.uri = uri          # absolute URI
        self.ctype = ctype
        self.tag = tag
        self.size = None
        # tree structre data
        self.children = []
        self.level = parent and parent.level+1 or 0

    def __str__(self):
        return '%s%s %s %s (%s)' % (
            '  ' * self.level,
            self.tag,
            self.uri,
            self.ctype,
            self.size,
        )
        

class Fetcher(object):
    """ Fetch resources recursively. """
    def __init__(self):
        self.to_fetch = []
        self.resource_list = []
        self.uri_set = sets.Set()

        
    def fetch(self, uri):
        self.append(None, '', uri, TEXT_HTML, '')
        while self.to_fetch:
            res = self.to_fetch.pop(0)
            append = lambda baseuri, uri, ctype, tag: \
                self.append(res, baseuri, uri, ctype, tag)
            if res.ctype == TEXT_HTML:
                fp = urllib2.urlopen(res.uri)
                scan_html(fp, res.uri, append)
                fp.close()
                # TODO: size
            elif res.ctype == TEXT_CSS:
                fp = urllib2.urlopen(res.uri)
                scan_css(fp, res.uri, append)
                fp.close()
        self._show_result(self.resource_list[0])
        print '%s resources fetched' % len(self.resource_list)
                
                
    def append(self, parent, baseuri, uri, ctype, tag):
        abs_uri = urlparse.urljoin(baseuri, uri)
        abs_uri = httputil.canonicalize(abs_uri)    # TODO: test
        if abs_uri in self.uri_set:
            log.warn('Skip repeated resource - %s %s' % (tag, uri))
            return
        res = Resource(parent, uri=abs_uri, ctype=ctype, tag=tag)
        if parent:
            parent.children.append(res)
        self.to_fetch.append(res)
        self.resource_list.append(res)
        self.uri_set.add(abs_uri)
        log.debug('append %s', str(res))
                    
    def _show_result(self, res):
        print str(res)
        for c in res.children:
            self._show_result(c)  
    
    
# ----------------------------------------------------------------------
# Testing

#2005-09-07
#http://realestate.crawford-co.org/cgi-bin/db2www.pgm/req.mbr/main?nuser=17:00:53&midf=&midn=
#http://creativecommons.org/
#http://lucene.apache.org/
#http://en.wikipedia.org/wiki/Moscow_Kremlin
#http://tungwaiyip.info/2003/movie/AhYing.html

# g:\>minds\weblib\snapshot.py file://localhost/bin/py_repos/mindretrieve/trunk/lib/snapshot_sample/opera/creativecommons/createcommons.html
# g:\>minds\weblib\snapshot.py file://localhost/x/creativecommons/createcommons.html


def main(argv):
    if len(argv) <= 1:
        print __doc__
        sys.exit(-1)

    # we don't even load cfg yet
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
        
    url = argv[1]
    f = Fetcher()
    f.fetch(url)                        
    
if __name__ =='__main__':
    main(sys.argv)
