import StringIO
import sys
import unittest

from minds import distillML
from minds import distillparse


class TestParseDistillML(unittest.TestCase):

    def testMAX_OUTPUT_TAG_LEN(self):
        # </h1> should be the longest tag
        self.assertEqual(len('</h1>'), distillML.Parser.MAX_OUTPUT_TAG_LEN)


    def testParse00(self):
        ''' test parsing a empty file (invalid without the header section) '''
        input = StringIO.StringIO('')
        meta, content = distillparse.parseDistillML(input)
        self.assertEqual(0, len(meta))
        self.assertEqual('', content)


    def testParse0(self):
        ''' test parsing a minimal file '''
        input = StringIO.StringIO('\n')                     # with an empty header
        meta, content = distillparse.parseDistillML(input)
        self.assertEqual(0, len(meta))
        self.assertEqual('', content)


    def testParseMeta(self):
        ''' test parsing header into meta dictionary '''
        input = StringIO.StringIO(' header1 : value1 \nHEADER2:value2\n\n')
        meta, content = distillparse.parseDistillML(input)
        self.assertEqual(2, len(meta))
        self.assertEqual('value1', meta['header1'])         # extra space should be trimmed
        self.assertEqual('value2', meta['header2'])         # header would be turned into lower case


    def testParseTags(self):
        header = '\n'                                       # empty header
        input = StringIO.StringIO(header + '<item><h1>*</h1></item>')
        meta, content = distillparse.parseDistillML(input)

        self.assertEqual('<item>*</item>', content)         # <h1> stripped, <item> stays


    def testParseTagSpanBuffer(self):

        header = '\n'                                                   # empty header
                                          # |123456789|123456789|       # tags span buffer boundary of 10
                                          # |         |         |
        input = StringIO.StringIO(header + 'abcdef<item>ghijk</li>lmn')
        meta, content = distillparse.parseDistillML(input, bufsize=10)          # bufsize of 10

        self.assertEqual('abcdef<item>ghijklmn', content)



if __name__ == '__main__':
    unittest.main()