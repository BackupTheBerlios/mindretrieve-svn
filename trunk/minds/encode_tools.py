"""Usage: encode_tools.py filename

See http://www.w3.org/International/tutorials/tutorial-char-enc/Overview.html#declaring

Precedence rules
* HTTP Content-Type
* XML declaration
* meta charset declaration
* link charset attribute
"""

import codecs
import logging
import sys

from toollib import sgmllib         # custom version of sgmllib
from util import rspreader


log = logging.getLogger('encodetool')

DEFAULT_ENCODING = 'iso-8859-1'

DEFAULT           = 'DEFAULT'
HTTP_CONTENT_TYPE = 'HTTP_CONTENT_TYPE'
XML_DECLARATION   = 'XML_DECLARATION'
META_CHARSET      = 'META_CHARSET'
LINK_CHARSET      = 'LINK_CHARSET'


def findCharSet(ctype):
    """ Parse content-type to find the charset parameter.
          e.g. 'text/html; charset=big5'
        See also RFC2616 3.4, 3.7
    """
    params = ctype.split(';')
    for p in params[1:]:
        if '=' not in p:
            continue
        n, v = p.split('=',1)
        if n.lower().strip() == 'charset':
            return v.lower().strip()
    return ''


def _getvalue(attrs, name):
    """ Helper to find the value correspond to name in attrs list. '' if not found. """
    for n, val in attrs:
        if n.lower() == name:
            return val
    return ''


class Parser(sgmllib.SGMLParser):
    """ Find the charset from http-equiv tag in the format of
            <META http-equiv="Content-Type" content="text/html; charset=big5">
    """

    def __init__(self):
        sgmllib.SGMLParser.__init__(self)
        self.reset()

    def reset(self):
        sgmllib.SGMLParser.reset(self)
        self.charset = ''

    def unknown_starttag(self, tag, attrs):
        if tag != 'meta':
            return
        if _getvalue(attrs,'http-equiv').lower() != 'content-type':
            return
        self.charset = findCharSet(_getvalue(attrs,'content'))
        raise StopIteration()



def findMetaHttpEquiv(first_block):
    parser = Parser()
    try:
        parser.feed(first_block)
    except StopIteration:               # good, found charset
        return parser.charset
    except sgmllib.SGMLParseError, e:   # todo: we care more about the charset than strictless, relax the error?
        log.exception('Error Parsing')
    except Exception, e:
        log.exception('Error Parsing')
    return ''


def determineEncoding(meta, first_block):
    """ Determine the message encoding by looking into HTTP header, XML
        declaration and meta tag.

        Return charset, source_id
    """

    # try http header
    if meta.has_key('content-type'):
        charset = findCharSet(meta['content-type'])
        if charset:
            return charset, HTTP_CONTENT_TYPE

    # todo: need to handle XHTML

    # try meta http-equiv
    charset =findMetaHttpEquiv(first_block)
    if charset:
        return charset, META_CHARSET

    # use default encoding
    return DEFAULT_ENCODING, DEFAULT



def getreader(encoding, source=DEFAULT):
    """ Simple forward to codecs.getreader and format a nice error message when things break. """
    try:
        return codecs.getreader(encoding)
    except LookupError, e:
        raise UnicodeError, '%s [source=%s]' % (e, source)



def main(argv):
    if len(argv) < 2:
        print __doc__
        sys.exit(-1)

    import messagelog, qmsg_processor

    filename = argv[1]

    fp = file(filename, 'rb')
    minfo = messagelog.MessageInfo.parseMessageLog(fp)
    meta = qmsg_processor._extract_meta(minfo,'')
    fp.close()

    fp = rspreader.openlog(filename)
    first_block = fp.read(8192)
    print 'Encoding:', determineEncoding(meta, first_block)


if __name__ == '__main__':
    main(sys.argv)
