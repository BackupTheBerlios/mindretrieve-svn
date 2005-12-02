from StringIO import StringIO
import unittest

import dsv

# list of (encoded string, decoded fields)
DATA = [
('',                ['']),                  # 0 field
(r'a',              ['a']),                 # 1 field
(r'a|b|c',          ['a','b','c']),         # 3 fields

(r'|b',             ['','b']),              # start with bar
(r'a|',             ['a','']),              # end with bar
(r'a||b',           ['a','','b']),          # consecutive bars
(r'\|a|b\||\|c\|',  ['|a','b|','|c|']),     # bars escaped

(r'\\a|b\\|\\c\\',  ['\\a','b\\','\\c\\']), # slashes escaped
(r'\\a|\\\||\|c\\', ['\\a','\\|','|c\\']),  # bars and slashes escaped

(r'1\n2|3\n\n4',    ['1\n2','3\n\n4']),     # \n escaped
(r'm\\n',           ['m\\n']),              # escape \, not \n
(r'\n1|2\n',        ['\n1','2\n']),         # start with \n, end with \n

(r'1\r2|3\r\n4',    ['1\r2','3\r\n4']),     # \r escaped
]

DATA1 = [
(r'\a|\b|\c',       ['a','b','c']),         # start with slash
(r'a|'+'\\',        ['a','']),              # end with slash
]

##SAMPLE_FILE = r"""
### Use '#' to denote a comment
##
### Blank line above is skipped
##
### Below is the header row. Character case, heading and trail blanks should be normalized
##field1| FIELD2 |Field3
##
### Rec1 - Empty record
##||
##
### Rec2 - spaces are stripped but character case  preserved
##a| B |c
##
### Rec3 - with escape characters
##\\a|\||line1\nline2
##"""

class TestDsv(unittest.TestCase):

    def test_encode_and_decode(self):
        # Test a round trip of decode and encode
        for line, result in DATA:
            self.assertEqual(dsv.decode_fields(line), result)
            self.assertEqual(dsv.encode_fields(result), line)

    def test_decode(self):
        # DATA1 are corner case for the parser (can't do round trip)
        for line, result in DATA1:
            self.assertEqual(dsv.decode_fields(line), result)

# 2005-12-02 dsv.parse() is disabled
#    def test_parse_file(self):
#        fp = dsv.parse(StringIO(SAMPLE_FILE))
#
#        # record1
#        lineno, fields = fp.next()
#        self.assertEqual(fields[0], '')
#        self.assertEqual(fields[1], '')
#        self.assertEqual(fields[2], '')
#
#        # record2
#        lineno, fields = fp.next()
#        self.assertEqual(fields[0], 'a')
#        self.assertEqual(fields[1], 'B')
#        self.assertEqual(fields[2], 'c')
#        # access as attribute
#        self.assertEqual(fields.field1, 'a')
#        self.assertEqual(fields.field2, 'B')
#        self.assertEqual(fields.field3, 'c')
#
#        # record3 with escape characters
#        lineno, fields = fp.next()
#        self.assertEqual(fields[0], '\\a')
#        self.assertEqual(fields[1], '|')
#        self.assertEqual(fields[2], 'line1\nline2')
#
#        self.assertRaises(StopIteration, fp.next)


if __name__ == '__main__':
    unittest.main()