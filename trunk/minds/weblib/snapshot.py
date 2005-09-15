"""Usage: snapshot.py url
"""

# CGI save and read to weblib dir
# character encoding default wrong? Content-Type: text/html; charset=ISO-8859-1
# why MIME-Version: 1.0 always?
# TODO: report progress, not parsing result or css error.
# TODO: make append generator?
# TODO: redirect, proxy, https
# TODO: character encoding, transfer-encoding
# TODO: give partial report when error happens
# TODO: handle fetching error
# TODO: httplib may not need to handle broken connection.
# TODO: always use httplib rather than urllib for http to reduce testing variation.
# TODO: https

# Resources
# ---------
# RFC1808 - Relative Uniform Resource Locators
#
# RFC2616 - Hypertext Transfer Protocol -- HTTP/1.1
#   14.14 Content-Location
#
# HTML 4.01 Specification (http://www.w3.org/TR/html401)
#   12 - Links
#   14 - Style Sheets
#
# CSS2 Specification (http://www.w3.org/TR/REC-CSS2)


# ----------------------------------------------------------------------------
#
# Snapshot
#
#
#  +-------------------------------+       +---------------------------------+
#  |Snapshot                       |       |Fetcher                          |
#  |-------------------------------|       |---------------------------------|
#  |Download, parse and traverse   |       |Fetch a series of URIs using     |
#  |linked documents. Manage the   |       |various transports. Use          |
#  |tree structured result.        |<>---->|optimization technique such as   |
#  |                               |       |HTTP persistent connection,      |
#  |                               |       |multiple connections to same     |
#  |                               |       |or different hosts, etc.         |
#  |                               |       |                                 |
#  +-------------------------------+       +---------------------------------+
#                 <>                                 |          <>
#                 |                                  |          |
#                 |                                  |          |
#                 |----------------------------------+          |
#                 |                                             |
#                 v*                                            v*
#  +------------------------+                   +---------------------------+
#  |Resource                |                   |ConnectionObject           |
#  |------------------------|  parent           |---------------------------|
#  |uri                     |<-----------+      |Maintain persistent HTTP   |
#  |content-type            |            |      |connection                 |
#  |content                 |            |      |                           |
#  |etc                     |* children  |      |                           |
#  |                        |<-----------+      |                           |
#  +------------------------+                   +---------------------------+
#



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


import cStringIO
import datetime
from email import Encoders
from email.Generator import Generator
from email.MIMEMultipart import MIMEMultipart
from email.MIMENonMultipart import MIMENonMultipart
import httplib
import logging
import Queue
import re
import sets
import StringIO
import sys
import urllib2
import urlparse

from cssutils.cssparser import *
from minds.config import cfg
from minds.util import html_pull_parser as hpp
from minds.util import httputil

log = logging.getLogger('snapshot')

APPLICATION = 'application/octet-stream'
TEXT_HTML = 'text/html'
TEXT_CSS = 'text/css'


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
#
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

    cp = CSSParser(loglevel=logging.ERROR)
    stylesheet = cp.parseString(fp.read().decode('UTF-8'))               ##HACK TODO encoding 
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

class Resource(object):
    """ Represents a resource fetched. """
    def __init__(self, parent, uri='', ctype='', tag=''):
        self.uri = uri          # absolute URI
        self.ctype = ctype
        self.tag = tag
        self.data = None
        self.size = None

        # tree structre data
        self.parent = parent
        self.children = []
        self.level = parent and parent.level+1 or 0

    def __str__(self):
        return '%s%s %s %s (%s)' % (
            '  ' * self.level,
            self.tag,
            self.ctype,
            self.uri,
            self.size,
        )


class Snapshot(object):
    """ Fetch resources recursively. """
    def __init__(self):
        self.resource_list = []
        self.uri_set = sets.Set()
        self.fetcher = Fetcher()


    def fetch(self, uri):
        self._append(None, '', uri, TEXT_HTML, '')
        while True:
            res = self.fetcher.dequeue()
            if not res:
                break
            log.debug('Fetching %s', res)
            res.data = res.fp.read()
            res.size = len(res.data)
            res.fp.close()
            res.ctype_actual = res.fp.getheader('content-type')
            
            append = lambda baseuri, uri, ctype, tag: \
                self._append(res, baseuri, uri, ctype, tag)
            if res.ctype == TEXT_HTML:
                scan_html(cStringIO.StringIO(res.data), res.uri, append)
            elif res.ctype == TEXT_CSS:
                scan_css(cStringIO.StringIO(res.data), res.uri, append)
                
        self.fetcher.close()

        t = self.fetcher.endtime - self.fetcher.starttime
        self._show_result(self.resource_list[0])
        print '%s bytes from %s resources fetched in %s' % (
            sum([r.size for r in self.resource_list]), 
            len(self.resource_list), 
            str(t)[2:7],
        )
        print '\nFetch report'
        print '\n'.join(['%s from %s' % (r[1], r[0]) for r in self.fetcher.report()])


    def _append(self, parent, baseuri, uri, ctype, tag):
        abs_uri = urlparse.urljoin(baseuri, uri)
        abs_uri = httputil.canonicalize(abs_uri)    # TODO: test
        if abs_uri in self.uri_set:
            #log.warn('Skip repeated resource - %s %s' % (tag, uri))
            return
        res = Resource(parent, uri=abs_uri, ctype=ctype, tag=tag)
        if parent:
            parent.children.append(res)
        self.resource_list.append(res)
        self.uri_set.add(abs_uri)
        self.fetcher.queue(res)


    def generate(self, fp):
        msg = MIMEMultipart(_subtype='related')
        msg['Subject'] = 'archived'
        msg.epilogue = ''   # Guarantees the message ends in a newline

        for res in self.resource_list:
            if '/' in res.ctype_actual:
                maintype, subtype = res.ctype_actual.split('/',1)
            else:    
                maintype, subtype = res.ctype_actual, ''
            part = MIMENonMultipart(maintype, subtype)
            part.set_payload(res.data)
            part['content-location'] = res.uri
            Encoders.encode_base64(part)
            msg.attach(part)
            
        # generate the MIME message    
        Generator(fp, False).flatten(msg)
        
        
    def _show_result(self, res):
        print str(res)
        for c in res.children:
            self._show_result(c)


# ----------------------------------------------------------------------
# Fetcher

MAX_HTTP_CONN = 10      # max number of persistent HTTP connection. Use one-off urllib2 if exceeded.
HTTP_CONN_TIMEOUT = 10  # timeout in number of seconds

HEADERS = {
'User-Agent': cfg.application_name,
}

class ConnectionObject(object):
    """ Object to maintain persistent HTTP connection. """
    def __init__(self, netloc):
        self.netloc = netloc
        self.lastused = None    # datetime
        self.conn = None        # HTTPConnection
        self.count = 0
    
    def connect(self):
        self.conn = httplib.HTTPConnection(self.netloc)
        self.conn.connect()
        
        
class Fetcher(object):

    def __init__(self):
        self.queue1 = []    # higher priority queue (HTML,CSS)
        self.queue2 = []    # lower priority queue
        self.conns = []     # list of ConnectionObject
        self.count = 0      # fetch count (not via conns)
        self.starttime = datetime.datetime.now()
        self.endtime = self.starttime

    def queue(self, res):
        if res.ctype in [TEXT_HTML, TEXT_CSS]:
            self.queue1.append(res)
        else:
            self.queue2.append(res)

    def dequeue(self):
        if self.queue1:
            res = self.queue1.pop(0)
        elif self.queue2:
            res = self.queue2.pop(0)
        else:
            return None        

        scheme, netloc, _, _, _, _ = urlparse.urlparse(res.uri)
        conn = scheme == 'http' and self._get_conn(netloc)
        if not conn:
            # non-http or no more room in self.conns
            res.fp = urllib2.open(res.uri)
            return res
        
        conn.conn.request('GET', res.uri, '', HEADERS)
        res.fp = conn.conn.getresponse()
        return res
     
    def _get_conn(self, netloc):
        for conn in self.conns:
            if conn.netloc == netloc:
                conn.count += 1
                return conn   
        # create new conn? 
        if len(self.conns) < MAX_HTTP_CONN:
            conn = ConnectionObject(netloc)
            self.conns.append(conn)
            conn.connect()
            conn.count += 1
            return conn
        return None    

    def close(self):
        for conn in self.conns:
            try:
                conn.conn.close()
            except:
                log.exception('Problem closing for %s' % netloc)
        self.endtime = datetime.datetime.now()
       
    def report(self):
        """ Return list of (netloc, count). '' is fetches not via conn """
        result = [('', self.count)]
        result.extend([(c.netloc, c.count) for c in self.conns])
        return result
       
       
        
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
# g:\>minds\weblib\snapshot.py http://localhost/ss/opera/wikipedia/Moscow_Kremlin.htm

def main(argv):
    if len(argv) <= 1:
        print __doc__
        sys.exit(-1)

    url = argv[1]
    snapshot = Snapshot()
    snapshot.fetch(url)                        
    fp = file('1.mhtml','wb')
    snapshot.generate(fp)
    fp.close()
    
if __name__ =='__main__':
    main(sys.argv)
