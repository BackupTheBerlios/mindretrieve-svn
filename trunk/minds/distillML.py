"""Usage: distillML.py [option] filename

options
  -d    distill an HTML or a mlog file
  -p    parse a distillML archive file


This module convert HTML into a distilled format by stripping most tags.
The purpose is to save storage space in the archive, and clean it enough
to be feed to the index engine. The goal of distillML are

1. As a readable document without the layout and style.
2. Easy to strip off the remaining tags to feed to the index engine.
3. The data should be compact for long term archival.
4. The data should be reasonable readable by human.

Secondly, the distill process also try to filter out documents that should not be
indexed. The reason includes

1. Non-HTML or binary documents being miscategorized as HTML.
2. Ads/Spam and other low value documents.
"""

import codecs
import logging
import re
import shutil
import string
import StringIO
import sys
from xml.sax import saxutils

from toollib import sgmllib         # custom version of sgmllib
from minds.config import cfg
from minds import domain_filter
from minds import encode_tools
from minds import messagelog
from minds.util import magic


log = logging.getLogger('distill')


def _collapse(s):
    """ collapse multiple whitespace as a single space char """
    return ' '.join(s.split())


def _getvalue(attrs, name):
    ''' Helper to find the value correspond to name in attrs list.
        Return '' if not found.
    '''
    for n, val in attrs:
        if n.lower() == name:
            return val
    return ''


def _hasattr(attrs, name):
    ''' Helper to find if attribute name is in the attrs list '''
    for n, val in attrs:
        if n.lower() == name:
            return True
    return False


class Parser(sgmllib.SGMLParser):

    # 24 Character entity references in HTML 4
    # http://www.w3.org/TR/REC-html40/sgml/entities.html

    # todo: add the whole set using unicode
    # keep &gt; and &lt; undecoded
    # 1. do not decode to create new tags to disrupt distillML
    # 2. keep it unencoded so that it is still readable in a cached document
    # Alternatively drop it altogether?
    entityref_map = {
        'amp' : '&',
        'gt'  : '&gt;',
        'lt'  : '&lt;',
        'nbsp': ' ',
        'quot': '"',
    }

    charref_map = {
        '187': '>',
    }

    # This is a list of tags should present in any 'normal' HTML
    # document. If none of these are found, the document is assume to be
    # non-html (maybe css, js?)
    #
    # Note: although you'll find a lot of 'p' or 'a' in CSS, they are
    # not parsed as tags as in the <p> or </a> format. tag are space delimited.
    COMMON_TAGS = ' p br hr h1 h2 h3 ul ol li a table tr td div span form input html body head title '

    WAIT_HEAD   = 1
    IN_HEAD     = 2
    IN_TITLE    = 3     # IN_TITLE must happen only when IN_HEAD
    IN_BODY     = 4     # either we find a <body> or we assume it is body where the tag is omitted.
    IN_IGNORE   = 5     # in tags like <script>

    state_name = {
        WAIT_HEAD: 'wait',
        IN_HEAD  : 'head',
        IN_TITLE : 'title',
        IN_BODY  : 'body',
        IN_IGNORE: 'ignore',
    }

    # these are the tags that outputs
    TAGS_USED = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'ul', 'ol', 'li', 'dl', 'dd', 'dt',
        'br', 'hr'
    ]

    # build the variations
    OUTPUT_TAG = ['<%s>' % t for t in TAGS_USED] + \
                 ['</%s>' % t for t in TAGS_USED]

    # the longest tag
    MAX_OUTPUT_TAG_LEN = max( map(len, OUTPUT_TAG) )



    def __init__(self, out):
        sgmllib.SGMLParser.__init__(self)
        self.out = out
        self.reset()


    def reset(self):
        sgmllib.SGMLParser.reset(self)

        self.meta = {}                  # collect title, description, keywords as meta data
        self.data = []
        self.state = self.WAIT_HEAD
        self.first_td = True

        self.has_frameset = False
        self.has_html_body = False
        self.has_common_tag = False


    def parse(self, reader, meta):
        """ The main action. """

        if meta != None:
            self.meta = meta

        while True:
            data = reader.read(65536)
            if not data: break
            self.feed(data)


    def flushdata(self):
        if self.data:
            self.out.out(self.data)
            self.data = []


    def getposStr(self):
        return '%03d %03d' % self.getpos()


    def _checkCommonTag(self, tag):
        tag = ' ' + tag + ' '                  # space delimit it
        if self.COMMON_TAGS.find(tag) >= 0:
            self.has_common_tag = True


    def changeState(self, tag):

        if self.state == self.WAIT_HEAD:
            if tag == 'html':
                pass
            elif tag == 'head':
                self.state = self.IN_HEAD
                self.data = []
            else:
                self.out.outHeader(self.meta)
                self.state = self.IN_BODY                           # any tag other <head> or <html> -> IN_BODY
                self.data = []

        elif self.state == self.IN_HEAD:
            if tag == 'title':
                self.state = self.IN_TITLE
                self.data = []
            if tag == 'body' or tag == '/head':                     # perhaps a missing </head>
                self.out.outHeader(self.meta)
                self.state = self.IN_BODY
                self.data = []

        elif self.state == self.IN_TITLE:
            if tag == '/title':
                self.meta['title'] = _collapse(' '.join(self.data))
                self.data = []
                self.state = self.IN_HEAD
            elif tag == '/head' or tag == 'body':                   # This handles a missing </title>
                self.meta['title'] = _collapse(' '.join(self.data))
                self.data = []

                self.out.outHeader(self.meta)
                self.state = self.IN_BODY

        elif self.state == self.IN_BODY:
            if tag in ['script', 'select', 'style']:
                self.state = self.IN_IGNORE

        elif self.state == self.IN_IGNORE:                           # todo: nested IGNORE? not welformed?
            if tag in ['/script', '/select', '/style']:
                self.state = self.IN_BODY

        else:
            raise RuntimeError, 'Invalid state %s' % self.state


    def unknown_starttag(self, tag, attrs):

        if not self.has_common_tag:
            self._checkCommonTag(tag)

        self.changeState(tag)

        if self.state == self.IN_BODY:
            self.flushdata()

        if tag == 'meta':
            name = _getvalue(attrs,'name').lower()
            content = _getvalue(attrs,'content')
            if name == 'description':
                self.meta['description'] = saxutils.unescape(_collapse(content))
            elif name == 'keywords':
                self.meta['keywords'] = saxutils.unescape(_collapse(content))

        elif tag == 'html':
            self.has_html_body = True

        elif tag == 'body':
            self.has_html_body = True

        elif tag == 'frameset':
            self.has_frameset = True

        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.out.outTag(tag)

        elif tag in ['p', 'div', 'pre']:
            self.out.outTag('p')

        elif tag in ['ul', 'ol', 'li', 'dl', 'dd', 'dt']:
            self.out.outTag(tag)

        elif tag in ['form', 'table']:
            self.out.outTag('p')

        elif tag in ['tr']:
            self.first_td = True

        elif tag in ['td','th']:
            if self.first_td:
                self.first_td = False
            else:
                self.data.append('   ')

        elif tag == 'input':

            itype = _getvalue(attrs, 'type')

            if itype == 'checkbox':
                if _hasattr(attrs,'checked'):
                    self.out.out('[*] ')
                else:
                    self.out.out('[ ] ')

            elif itype == 'radio':
                if _hasattr(attrs,'checked'):
                    self.out.out('(*) ')
                else:
                    self.out.out('( ) ')

            elif itype == 'image':
                alt = _getvalue(attrs, 'alt') or _getvalue(attrs, 'value')
                self.out.outAlt(saxutils.unescape(alt))

            elif itype == 'password':
                self.out.outAlt('***')

            elif itype == 'hidden':
                pass

            else:
                value = _getvalue(attrs, 'value')
                self.out.outAlt(saxutils.unescape(value))

        # todo: wrap the button text with [].
        #elif tag == 'button':
        #    pass

        elif tag == 'br':
            self.out.outTag('br')

        elif tag == 'img':
            alt = _getvalue(attrs, 'alt')
            if alt:
                self.out.outAlt(saxutils.unescape(alt))

        elif tag == 'hr':
            self.out.outTag('hr')


    def unknown_endtag(self, tag):

        self.changeState('/'+tag)

        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.flushdata()
            self.out.outTag('/'+tag)

        elif tag in ['tr']:
            self.flushdata()
            self.out.outTag('br')

        elif tag in ['ul', 'ol', 'li', 'dl', 'dd', 'dt']:
            self.flushdata()
            self.out.outTag('/'+tag)

        elif tag == 'textarea':
            value = _collapse(' '.join(self.data))
            self.data = []
            self.out.outAlt(value)

        elif tag in ['body' or 'html']:
            self.flushdata()


    def handle_data(self, data):
        if self.state in [self.WAIT_HEAD, self.IN_BODY, self.IN_TITLE]:
            self.data.append(data)


    def handle_charref(self, name):
        c = self.charref_map.get(name,'')
        if c: self.handle_data(c)
        # OK to drop special symbols because we can't index it


    def handle_entityref(self, name):
        c = self.entityref_map.get(name,'')
        if c: self.handle_data(c)



class DebugParser(Parser):

    def unknown_starttag(self, tag, attrs):
        print '[%6s] <%s>' % (self.state_name.get(self.state,'?'), tag)
        Parser.unknown_starttag(self, tag, attrs)


    def unknown_endtag(self, tag):
        print '[%6s] </%s>' % (self.state_name.get(self.state,'?'), tag)
        Parser.unknown_endtag(self, tag)


    def handle_data(self, data):
        print '[%6s] %s' % (self.state_name.get(self.state,'?'), data)
        Parser.handle_data(self, data)



def writeHeader(fp, meta):
    """ Output meta data to the beginning of archived file """

    fp.write('uri: %s\n'  % meta.get('uri' , ''))
    fp.write('date: %s\n' % meta.get('date', ''))
    if meta.has_key('title'        ): fp.write('title: %s\n'        % meta['title'        ])
    if meta.has_key('description'  ): fp.write('description: %s\n'  % meta['description'  ])
    if meta.has_key('keywords'     ): fp.write('keywords: %s\n'     % meta['keywords'     ])
    if meta.has_key('etag'         ): fp.write('etag: %s\n'         % meta['etag'         ])
    if meta.has_key('last-modified'): fp.write('last-modified: %s\n'% meta['last-modified'])
    fp.write('\n')



class Formatter:

    SPACE = ' '

    def __init__(self, wfile, header_len=0, visiblechar_needed=0):

        self.wfile = wfile

        self.header_sent = False

        # these parameters help to analysis the HTML document
        self.visiblechar_needed = visiblechar_needed
        self.header_count = header_len
        self.header = StringIO.StringIO()

        self.lastTag = None             # immediate last tag
        self.lastTrailingSpace = False  # a trailing space not yet output
                                        # note: At EOF if the trailing space is not used, drop it.


    def outHeader(self, meta):
        writeHeader(self.wfile, meta)
        self.header_sent = True


    def countCharacters(self, txt):
        """ Do some statistics on the output """

        # check how much it fulfills the visible character counter
        if self.visiblechar_needed > 0:
            for c in txt:
                if c not in string.whitespace:
                    self.visiblechar_needed -= 1
                    if self.visiblechar_needed <= 0:
                        break

        if self.header_count > 0:
            h = txt.lstrip()
            self.header.write(h[:self.header_count])
            self.header_count -= len(h)    # could go negative


    def out(self, txt):

        if not txt: return

        if hasattr(txt,'append'):   # txt is a list of text?
            txt = ''.join(txt)
            if not txt: return

        if not self.header_sent: return

        # specifically check for heading and trailing space
        # because _collapse() aggressively remove whitespace at both ends
        # also to collapse space between calls to out()
        has_heading_space  = txt[:1] in string.whitespace
        has_trailing_space = txt[-1:] in string.whitespace
        txt = _collapse(txt)

        # txt is entirely whitespace?
        if not txt:
            if not self.lastTag:    # if has lastTag, ignore this space
                self.lastTrailingSpace = True
            return

        self.countCharacters(txt)

        # output one space if any of the condition below is true
        # note: lastTag and lastTrailingSpace is mutually exclusive
        has_space = self.lastTrailingSpace or (has_heading_space and not self.lastTag)
        if has_space:
            self.wfile.write(self.SPACE)
            self.lastTrailingSpace = False

        self.wfile.write(txt)

        # don't output trailing space yet.
        self.lastTrailingSpace = has_trailing_space
        self.lastTag = None


    def outAlt(self, txt):

        if not self.header_sent: return

        if self.lastTrailingSpace:
            self.wfile.write(self.SPACE)
            self.lastTrailingSpace = False

        self.wfile.write('[')
        self.wfile.write(txt)
        self.wfile.write(']')

        self.lastTag = None
        self.lastTrailingSpace = True


    def outTag(self, tag):

        if not self.header_sent: return

        # collapse tags
        if (tag == 'p' or tag == 'br') and tag == self.lastTag:
            return

        # ignore lastTrailingSpace before a tag

        if tag == 'br':
            self.wfile.write('<br>\n')
        elif tag[0:1] == '/':
            self.wfile.write('<')
            self.wfile.write(tag)
            self.wfile.write('>')
        else:
            self.wfile.write('\n<')
            self.wfile.write(tag)
            self.wfile.write('>')

        self.lastTag = tag
        self.lastTrailingSpace = False


    def getHeader(self):
        return self.header.getvalue()


    def isVisible(self):
        return self.visiblechar_needed <= 0



# Problem:
# Web server in the real world are often not configure properly to sent
# correct content-type. Browser often need to infer the content-type
# regardless of the content-type header. Commonly resources are linked
# inline via these tags. Therefore the browser should a good idea what
# the media might be base on the tag that reference them, e.g. <img> link
# to images, <script> links to javascripts.
#
# <img>
# <script>
# <link>
# <iframe>
#
# In addition, IE infer content-type even for resources referneced via <a>


# todo: lowercase, normalize, get a large test set from cache?
JAVASCRIPT_FUNCTION = re.compile('function .*\(')   # move this to magic

PARSE_ERROR = -1    # exception from parser
EXDOMAIN    = 1     # excluded domain
NON_HTML    = 2     # recognized by several detection rules
FRAMESET    = 3     # reject frameset document
LOWVISIBLE  = 4     # at least 15 visible characters needed (match a few types of ads; single <img>, etc.)

MIN_VISIBLECHAR = 32    # assert that if a doc has less number of chars, it is not worth indexing.
                        # This catch a lot of ads!
                        # On the other hand it also catch some picture windows with only a short caption.
                        # todo: should we include title & description as part of content?


def preparse_filter(first_block, meta):
    """ Filter by domain and magic header.
        Returns distill result
    """
    uri = meta.get('uri','')
    dm = domain_filter.match(uri)
    if dm:
        return EXDOMAIN, dm

    guessed = magic.guess_type(first_block)
    if guessed and guessed != 'text/html' and guessed != 'text/plain':
        return NON_HTML, guessed

    return 0



def distill(rstream, wstream, meta):
    """ Parse the HTML doc rstream. Determine its character encoding.
        Return buf and fill in meta.
        Use heuristic to determine if it should be indexed.
        Return False if not.

        @params rstream - the input stream
        @params wstream - the distilled output stream (utf8 encoded)
        @params meta - Add the title, description and keywords fields while parsing.
                       Also add encoding (for diagnosis)
                       Other meta data like uri and timestamp is supplied by caller.
        @returns - 0 means accepted. Otherwise a tuple of reason code and an explanation string.
    """

    first_block = rstream.read(8192)
    rstream.seek(0)                                           # network stream would not support seek!?

    result = preparse_filter(first_block, meta)
    if result:
        return result

    encoding, source = encode_tools.determineEncoding(meta, first_block)
    Reader = encode_tools.getreader(encoding, source)
    reader = Reader(rstream, 'replace')
    writer = codecs.getwriter('utf8')(wstream,'replace')

    meta['encoding'] = '%s [%s]' % (encoding, source)
    formatter = Formatter(writer, header_len=256, visiblechar_needed=MIN_VISIBLECHAR)
    parser = Parser(formatter)
    try:
        parser.parse(reader, meta)
    except sgmllib.SGMLParseError, e:
        return (PARSE_ERROR, 'SGMLParseError: %s' % str(e)) # SGMLParseError
    except Exception, e:
        log.exception('Error parsing: %s', reader)          # unknown exception
        return (PARSE_ERROR, str(e))


    # If it does not have any common tag it is presumed to be non-html
    # misconfigured as such.
    #
    # Note: we may miss some plain text document, which should still be
    # good for indexing. This risk should be low as the document would
    # appear scrambled in the browser if this happends (Well unless it is
    # contain in an iframe this may make some sense?)
    if not parser.has_common_tag:
        return (NON_HTML, 'unknown')    # todo: want to take a guess on CSS or JS? bet it in magic?

    if parser.has_frameset:
        return (FRAMESET, '<frameset>')

    # do some heurisitic analysis to weed out files that should not be indexed.
    header = formatter.getHeader()

    if not parser.has_html_body:
        if header.find('document.write') >= 0:  # also document *. *writeln
            return (NON_HTML, 'application/x-javascript')
        elif JAVASCRIPT_FUNCTION.search(header) and header.find('{') >= 0:
            return (NON_HTML, 'application/x-javascript')

    if formatter.visiblechar_needed > 0:
        return (LOWVISIBLE, header[:80])

    return 0



def distillTxt(rstream, wstream, meta):
    """ Similar interface to distill() for text/plain media type

        @params rstream - the input stream
        @params wstream - the output stream (meta data + content of rstream, utf8 encoded)
        @params meta - meta data like uri and timestamp is supplied by caller.
                       No title or description defined for plain text.
        @returns - 0 means accepted. Otherwise a tuple of reason code and an explanation string.
    """

    first_block = rstream.read(8192)
    rstream.seek(0)

    result = preparse_filter(first_block, meta)
    if result:
        return result

    encoding, source = encode_tools.determineEncoding(meta, first_block)
    Reader = encode_tools.getreader(encoding, source)
    reader = Reader(rstream, 'replace')
    writer = codecs.getwriter('utf8')(wstream,'replace')

    meta['encoding'] = '%s [%s]' % (encoding, source)

    writeHeader(writer, meta)
    shutil.copyfileobj(reader, writer)

    return 0



# ----------------------------------------------------------------------
# Cmdline util/testing

import pprint
from minds.util import rspreader

def test_distill(fp, wfile, meta):

    # build meta from rsp_header
    minfo = messagelog.MessageInfo.parseMessageLog(fp)
    meta.clear()
    meta.update(minfo.rsp_headers)

    # read content
    fp.seek(0)
    fp = rspreader.openlog(fp)

    return distill(fp, wfile, meta)


def test_parse(rfile):
    meta = {}
    formatter = Formatter(sys.stdout, header_len=256, visiblechar_needed=MIN_VISIBLECHAR)
    parser = DebugParser(formatter)
    try:
        parser.parse(rfile, meta)
    except sgmllib.SGMLParseError, e:
        return (PARSE_ERROR, 'HTMLParseError: %s' % str(e)) # SGMLParseError
    except Exception, e:
        log.exception('Error parsing: %s', rfile)           # unknown exception
        return (PARSE_ERROR, str(e))


def main(argv):
    if len(argv) < 3:
        print __doc__
        sys.exit(-1)

    if sys.platform == "win32":
        import msvcrt, os
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        # 01/13/05 note: my experience is you cannot pipe UTF16 output from a shell
        # to a file even with os.O_BINARY setting. Must write to file directly.

    option = argv[1]
    filename = argv[2]
    fp = file(filename,'rb')
    if option == '-d':
        meta = {}
        result = test_distill(fp, sys.stdout, meta)
        print >>sys.stderr
        print >>sys.stderr, '-'*72
        print >>sys.stderr, 'Meta:',
        pprint.pprint(meta, sys.stderr)

    elif option == '-p':
        fp = rspreader.openlog(fp)
        result = test_parse(fp)
        print >>sys.stderr
        print >>sys.stderr, '-'*72
        print >>sys.stderr, 'Result:', result

    else:
        print __doc__
        sys.exit(-1)

    fp.close()



if __name__ == '__main__':
    main(sys.argv)