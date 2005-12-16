"""Usage: html_pull_parser.py filename
"""

import htmlentitydefs
import sys

from toollib import sgmllib         # a custom version of sgmllib

# todo: HtmlPullParser has two purposes, it fixes some SGMLParser issue and it generates the tokens
#       Break into 2 classes?


DATA, TAG, ENDTAG, COMMENT = range(1,5)

class HtmlPullParser(sgmllib.SGMLParser):

    retain_entityref = {
      'gt' : 1,
      'lt' : 1,
      'amp': 1,
    }

    def __init__(self, verbose=0, comment=False):
        self.stream = []
        self.includeComment = comment
        sgmllib.SGMLParser.__init__(self, verbose)

    def handle_data(self, data):
        self.stream.append((DATA,data))

    # 30% performance improvement on parsing by short circuiting SGMLParser.unknown_starttag & unknown_endtag
    #def unknown_starttag(self, tag, attrs):
        #print '__%s__' % self._SGMLParser__starttag_text #str(self.__dict__)
    def finish_starttag(self, tag, attrs):
        self.stream.append((TAG, tag, attrs))
        return -1

    #def unknown_endtag(self, tag):
    def finish_endtag(self, tag):
        self.stream.append((ENDTAG, tag))

    #def unknown_entityref(self, ref):
    def handle_entityref(self, ref):

        # override handle_entityref() because it converts &gt; etc to >
        if self.retain_entityref.has_key(ref):
            self.stream.append((DATA,'&%s;'%ref))
            return

        try:
            ch = htmlentitydefs.name2codepoint[ref]
        except KeyError:
            pass
        else:
            self.stream.append((DATA,unichr(ch)))

    #def unknown_charref(self, ref):
    # note the original handle_charref just isn't good enough to handle unicode
    def handle_charref(self, name):
        try:
            if name[:1].lower() == 'x':      # e.g. &#xE5; -> name='xE5'
                ch = int(name[1:],16)
            else:
                ch = int(name)
        except ValueError:
            pass
        else:
            self.stream.append((DATA,unichr(ch)))

    def handle_comment(self, comment):
        if self.includeComment:
            self.stream.append((COMMENT,comment))

    def unknown_decl(self, data):
        # Treat XML CDATA block <![CDATA[...]]> as data
        # Are we stretching sgmllib here?
        if data[:6].lower() == 'cdata[':
            self.stream.append((DATA, data[6:]))
            # TODO: test

    MAX_DECLARATION = 32768

    def parse_declaration(self, i):
        """ A more lenient version of parse_declaration.
            In case of invalid declaration, skip everything between <!...>
            instead of throwing SGMLParseError.
        """
        try:
            # below is a workaround of a bug in markupbase.parse_declaration()
            j = i + 2
            if self.rawdata[j:j+2] in ("-", ""):         # markupbase wrongly used [j:j+1]
                return -1
            elif self.rawdata[j:j+1] == '-':
                raise sgmllib.SGMLParseError, 'Invalid markup ' + self.rawdata[i:i+4]

            return sgmllib.SGMLParser.parse_declaration(self, i)
        except sgmllib.SGMLParseError, e:
            j = self.rawdata.find('>', i)
            if j  >= 0:                                         # skip
                return j+1
            if len(self.rawdata) < i+self.MAX_DECLARATION:      # incomplete declaration
                return -1
            raise e                                             # too much to lookahead, treat as error



BUFSIZE = 32768

def generate_tokens(fp,comment=False):
    parser = HtmlPullParser(comment=comment)
    while True:
        data = fp.read(BUFSIZE)
        if data:
            parser.feed(data)
        else:
            parser.close()
        if not parser.stream:
            raise StopIteration
        for token in parser.stream:
            yield token
        parser.stream = []

# TODO: migrate generate_tokens to generate_tokens3
# TODO: migrate test
def generate_tokens3(fp,comment=False):
    """ Parse HTML and yield (kind, data, attrs) """
    parser = HtmlPullParser(comment=comment)
    while True:
        data = fp.read(BUFSIZE)
        if data:
            parser.feed(data)
        else:
            parser.close()
        if not parser.stream:
            raise StopIteration
        for token in parser.stream:
            if len(token) == 2:
                yield (token[0], token[1], None)
            else:
                yield token
        parser.stream = []


def main(argv):
    fp = file(argv[1],'rb')
    for t in generate_tokens(fp):
        print t


if __name__ == '__main__':
    main(sys.argv)