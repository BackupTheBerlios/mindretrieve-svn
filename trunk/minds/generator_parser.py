"""Usage: generator_parser.py filename
"""

import htmlentitydefs
import sys

from toollib import sgmllib         # custom version of sgmllib

DATA    = 1
TAG     = 2
ENDTAG  = 3

class GeneratorParser(sgmllib.SGMLParser):

    retain_entityref = {
      'gt' : 1,
      'lt' : 1,
      'amp': 1,
    }

    def __init__(self, verbose=0):
        self.stream = []
        sgmllib.SGMLParser.__init__(self, verbose)

    def handle_data(self, data):
        self.stream.append((DATA,data))

    def unknown_starttag(self, tag, attrs):
        #print '__%s__' % self._SGMLParser__starttag_text #str(self.__dict__)
        self.stream.append((TAG, tag, attrs))

    def unknown_endtag(self, tag):
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

    def unknown_charref(self, ref):
        try:
            if ref[:1].lower() == 'x':      # e.g. &#xE5; -> ref='xE5'
                ch = int(ref[1:],16)
            else:
                ch = int(ref)
        except ValueError:
            pass
        else:
            self.stream.append((DATA,unichr(ch)))

    def unknown_decl(self, data):
        pass


def generate_tokens(fp):
    parser = GeneratorParser()
    while True:
        data = fp.read(32768)
        if data:
            parser.feed(data)
        else:
            parser.close()
        if not parser.stream:
            raise StopIteration
        for token in parser.stream:
            yield token
        parser.stream = []


def main(argv):
    fp = file(argv[1],'rb')
    for t in generate_tokens(fp):
        print t


if __name__ == '__main__':
    main(sys.argv)