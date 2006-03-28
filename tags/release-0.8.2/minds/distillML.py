"""Usage: distillML.py [option] filename

options
  -d    distill an HTML or a mlog file


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

from minds.config import cfg
from minds import domain_filter
from minds import encode_tools
from minds import messagelog
from minds.util import html_pull_parser
from minds.util import magic
from toollib import sgmllib         # custom version of sgmllib

# todo: common tag
# todo: formatter intelligent
# todo: parse return tags seen
# todo: writeHeader ensure no line break

#elif id == sBODY:
### TODO: hack, body is optional
### TODO: outtag also start it?
##  naked html?
#   hello
#   <p>2
#   logic in out?


log = logging.getLogger('distill')

DATA    = html_pull_parser.DATA
TAG     = html_pull_parser.TAG
ENDTAG  = html_pull_parser.ENDTAG


# todo: collapse is not good for asian text.
# todo: line break turn into a space character separating words
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




# This is a list of tags should present in any 'normal' HTML
# document. If none of these are found, the document is assume to be
# non-html (maybe css, js?)
#
# Note: although you'll find a lot of 'p' or 'a' in CSS, they are
# not parsed as tags as in the <p> or </a> format. tag are space delimited.
COMMON_TAGS = ' p br hr h1 h2 h3 ul ol li a table tr td div span form input html body head title '


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



# process starttag
sHTML      =  1
sHEAD      =  2
sMETA      =  3
sTITLE     =  4
sBODY      =  5
sFRAMESET  =  6
sSTYLE     =  7
sSCRIPT    =  8
sSELECT    =  9
sOUTTAG    = 10
sOUTP      = 11
sTR        = 12
sTDTH      = 13
sINPUT     = 14
sIMG       = 15
sMisc      = 16


starttag_dict = {
    'html'      : sHTML,
    'head'      : sHEAD,
    'meta'      : sMETA,
    'title'     : sTITLE,
    'body'      : sBODY,
    'frameset'  : sFRAMESET,
    'style'     : sSTYLE,
    'script'    : sSCRIPT,
    'select'    : sSELECT,

    # other tags are grouped by how it is processed
    'h1'        : sOUTTAG,
    'h2'        : sOUTTAG,
    'h3'        : sOUTTAG,
    'h4'        : sOUTTAG,
    'h5'        : sOUTTAG,
    'h6'        : sOUTTAG,
    'p'         : sOUTP,
    'div'       : sOUTP,
    'pre'       : sOUTP,
    'ul'        : sOUTTAG,
    'ol'        : sOUTTAG,
    'li'        : sOUTTAG,
    'dl'        : sOUTTAG,
    'dd'        : sOUTTAG,
    'dt'        : sOUTTAG,
    'form'      : sOUTP,
    'table'     : sOUTP,
    'tr'        : sTR,
    'td'        : sTDTH,
    'th'        : sTDTH,
    'input'     : sINPUT,
    'img'       : sIMG,
    'br'        : sOUTTAG,
    'hr'        : sOUTTAG,

    # these tags are not processed, but they are counted as a common tag
    'a'         : sMisc,
    'span'      : sMisc,
}


# process endtag

eCLOSE_TAG   = 1
eBREAK_LINE  = 2
eSHOW_ALT    = 3
endtag_dict = {
    'h1'        : eCLOSE_TAG,
    'h2'        : eCLOSE_TAG,
    'h3'        : eCLOSE_TAG,
    'h4'        : eCLOSE_TAG,
    'h5'        : eCLOSE_TAG,
    'h6'        : eCLOSE_TAG,
    'tr'        : eBREAK_LINE,
    'ul'        : eCLOSE_TAG,
    'ol'        : eCLOSE_TAG,
    'li'        : eCLOSE_TAG,
    'dl'        : eCLOSE_TAG,
    'dd'        : eCLOSE_TAG,
    'dt'        : eCLOSE_TAG,
}


def process(fp, out, meta):
    """ Return has_html, has_frameset """

    has_html        = False
    has_frameset    = False
    has_common_tag  = False

    first_td    = False     # state for iterating td inside tr

    iterator = html_pull_parser.generate_tokens(fp)

    # General HTML format
    # <html>
    #   <head>
    #   <body>
    #
    # However all elements are optional.
    # It is better to use a flat, stateless loop to process elements

    for token in iterator:

        if token[0] == DATA:
            out.out(token[1])

        elif token[0] == TAG:

            tag = token[1]
            id = starttag_dict.get(tag,-1)

            if id > 0:
                has_common_tag = True

            if id == sOUTP:
                out.outTag('p')

            elif id == sOUTTAG:
                out.outTag(tag)

            elif id == sTR:
                first_td = True

            elif id == sTDTH:
                if first_td:
                    first_td = False
                else:
                    out.out('   ')

            elif id == sINPUT:

                attrs = token[2]
                itype = _getvalue(attrs, 'type')

                if itype == 'checkbox':
                    if _hasattr(attrs,'checked'):
                        out.out('[*] ')
                    else:
                        out.out('[ ] ')

                elif itype == 'radio':
                    if _hasattr(attrs,'checked'):
                        out.out('(*) ')
                    else:
                        out.out('( ) ')

                elif itype == 'image':
                    alt = _getvalue(attrs, 'alt') or _getvalue(attrs, 'value')
                    out.outAlt(saxutils.unescape(alt))

                elif itype == 'password':
                    out.outAlt('***')

                elif itype == 'hidden':
                    pass

                else:
                    value = _getvalue(attrs, 'value')
                    out.outAlt(saxutils.unescape(value))

            elif id == sIMG:
                attrs = token[2]
                alt = _getvalue(attrs, 'alt')
                if alt:
                    out.outAlt(saxutils.unescape(alt))

            elif id == sHTML:
                has_html = True
                out.notifyHtml()

            elif id == sBODY:
                out.outHeader(meta)

            elif id == sFRAMESET:
                has_frameset = True

            elif id == sTITLE:
                title = ''
                for token in iterator:
                    if token[0] == DATA:
                        title += token[1]
                    elif token in [
                        (ENDTAG, 'title'),  # only </title> is valid
                        (ENDTAG, 'head'),   # in case no </title>
                        (TAG, 'body'),      # in case no </title>
                        ]:
                        break
                meta['title'] = _collapse(title)

            elif id == sMETA:
                attrs = token[2]
                name = _getvalue(attrs,'name').lower()
                content = _getvalue(attrs,'content')
                if name == 'description':
                    meta['description'] = saxutils.unescape(_collapse(content))
                elif name == 'keywords':
                    meta['keywords'] = saxutils.unescape(_collapse(content))

            elif id == sSCRIPT:
                for token in iterator:
                    if token == (ENDTAG, 'script'):
                        break

            elif id == sSTYLE:
                for token in iterator:
                    if token == (ENDTAG, 'style'):
                        break

            elif id == sSELECT:
                for token in iterator:
                    if token == (ENDTAG, 'select'):
                        break


        elif token[0] == ENDTAG:

            tag = token[1]
            id = endtag_dict.get(tag,-1)

            if id == eCLOSE_TAG:
                out.outTag('/'+tag)

            elif id == eBREAK_LINE:
                out.outTag('br')

    out.close(meta)

    return has_html, has_frameset, has_common_tag




def _writeOptionalHeader(fp, meta, header):
    value = meta.get(header)
    if value: fp.write(u'%s: %s\n' % (header, value))


def writeHeader(fp, meta):
    """ Output meta data to the beginning of archived file """

    fp.write(u'uri: %s\n'  % meta.get('uri' , ''))
    fp.write(u'date: %s\n' % meta.get('date', ''))
    _writeOptionalHeader( fp, meta, 'title'        )
    _writeOptionalHeader( fp, meta, 'description'  )
    _writeOptionalHeader( fp, meta, 'keywords'     )
    _writeOptionalHeader( fp, meta, 'etag'         )
    _writeOptionalHeader( fp, meta, 'last-modified')
    _writeOptionalHeader( fp, meta, 'referer'      )
    fp.write('\n')



class Formatter:

    SPACE = ' '
    HEADER_LEN = 256                    # collect the beginning of output

    # Note that initially we buffer output to 'buf' until:
    #
    # 1. header is output, and
    # 2. Certain amount of text is collected (HEADER_LEN)
    #
    # Once switchBuffer() is called the output will be sent directly to
    # the supplied wfile.

    def __init__(self, wfile):

        self.actual_wfile = wfile
        self.buf = StringIO.StringIO()
        self.wfile = self.buf           # temporary output to 'buf'

        self.header_sent = False
        self.content_size = 0
        self.htmlTagPos = -1

        self.lastTag = None             # immediate last tag, None if last output is text.
        self.lastTrailingSpace = False  # a trailing space not yet output
                                        # note: At EOF if the trailing space is not used, drop it.

    def switchBuffer(self):
        # Note that we won't switch until header is sent.
        # This mean any html without </head> or <body> to signal completion
        # of HEAD section would stuck in buffered mode and is less efficient.
        if self.actual_wfile and self.header_sent:
            self.actual_wfile.write(self.wfile.getvalue())
            self.wfile = self.actual_wfile
            self.actual_wfile = None


    def close(self, meta):
        # make sure actions below are carried out.
        # No harm if already called.
        self.outHeader(meta)
        self.switchBuffer()


    def notifyHtml(self):
        """ Call this when <html> is encountered """
        if self.htmlTagPos < 0:                     # ignore if more than 1 <html>
            self.htmlTagPos = self.content_size


    def outHeader(self, meta):
        if not self.header_sent:
            writeHeader(self.actual_wfile, meta)
            self.header_sent = True


    def out(self, txt):

        if not txt: return

        # specifically check for heading and trailing space
        # because _collapse() aggressively remove whitespace at both ends
        # also to collapse space between calls to out()
        has_heading_space  = txt[:1] in string.whitespace
        has_trailing_space = txt[-1:] in string.whitespace
#        txt = _collapse(txt)
        txt = ' '.join(txt.split())
        # txt is entirely whitespace?
        if not txt:
            if not self.lastTag:    # if has lastTag, ignore this space
                self.lastTrailingSpace = True
            return

        # output one space if any of the condition below is true
        # note: lastTag and lastTrailingSpace is mutually exclusive
        has_space = self.lastTrailingSpace or (has_heading_space and not self.lastTag)
        if has_space:
            self.wfile.write(self.SPACE)
            self.lastTrailingSpace = False

        self.wfile.write(txt)
        self.content_size += len(txt)
        if self.actual_wfile:
            if self.content_size > self.HEADER_LEN:
                self.switchBuffer()

        # don't output trailing space yet.
        self.lastTrailingSpace = has_trailing_space
        self.lastTag = None


    def outAlt(self, txt):

        if self.lastTrailingSpace:
            self.wfile.write(self.SPACE)
            self.lastTrailingSpace = False

        self.wfile.write('[')
        self.wfile.write(txt)
        self.wfile.write(']')

        self.lastTag = None
        self.lastTrailingSpace = True


    def outTag(self, tag):

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
        return self.buf.getvalue()


    def contentBeforeHtml(self):
        buf = self.buf.getvalue()
        if self.htmlTagPos < 0:
            return buf
        return buf[:self.htmlTagPos]



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
JS          = 3     # presume javascript
FRAMESET    = 4     # reject frameset document
LOWVISIBLE  = 5     # at least 15 visible characters needed (match a few types of ads; single <img>, etc.)

MIN_VISIBLECHAR = 32    # assert that if a doc has less number of chars, it is not worth indexing.
                        # This catch a lot of ads!
                        # On the other hand it also catch some picture windows with only a short caption.


js_rexp = '|'.join([
"(var\s+\w+\s*=)",              # var pophtml =
"(^\s*\w+\s*=\s*[\"\'\(])",     # ibHtml1="
"(document.write\s*\()",        # document.write(
"(function\s+\w+.*?{)",         # function YADopenWindow(x){
])

js_pattern = re.compile(js_rexp,re.MULTILINE)




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

    first_block = rstream.read(32768)
    rstream.seek(0)                                           # network stream would not support seek!?

    result = preparse_filter(first_block, meta)
    if result:
        return result

    encoding, source = encode_tools.determineEncodingLenient(meta, first_block)
    Reader = encode_tools.getreader(encoding, source)
    reader = Reader(rstream, 'replace')
    writer = codecs.getwriter('utf8')(wstream,'replace')

    meta['encoding'] = '%s [%s]' % (encoding, source)

    formatter = Formatter(writer)
    try:
        has_html, has_frameset, has_common_tag = process(reader, formatter, meta)
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
    if not has_common_tag:
        return (NON_HTML, 'unknown')    # todo: want to take a guess on CSS or JS? bet it in magic?

    if has_frameset:
        return (FRAMESET, '<frameset>')

    # do some heurisitic analysis to weed out files that should not be indexed.
    header = formatter.getHeader()

    # check for jsscript. Only two unusually places are checked
    # 1. If no <html>, the entire data
    # 2. If there is <html>, data before the <html>

    jscheck = formatter.contentBeforeHtml()
    m = js_pattern.search(jscheck)
    if m: return (JS, m.group(0)[:30])

    # If there is too little content (exclude <img alt>) do not index it
    # Indeed this catches a lot of ads.
    # todo: collapse space first?
    if formatter.content_size < MIN_VISIBLECHAR:
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

    encoding, source = encode_tools.determineEncodingLenient(meta, '')
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
    try:
        minfo = messagelog.MessageInfo.parseMessageLog(fp)
    except:
        pass    # assume it is html file (not mlog)
    else:
        meta.clear()
        meta.update(minfo.rsp_headers)

    # read content
    fp.seek(0)
    fp = rspreader.openlog(fp)

    return distill(fp, wfile, meta)



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
        print >>sys.stderr, 'Result:', result

    else:
        print __doc__
        sys.exit(-1)

    fp.close()



if __name__ == '__main__':
    main(sys.argv)