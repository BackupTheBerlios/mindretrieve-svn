"""
"""

import os, os.path, sys
import StringIO
import unittest

#from config_help import cfg
from minds import encode_tools



class TestEncodeTools(unittest.TestCase):

    def test_findCharSet0(self):
        self.assertEqual('', encode_tools.findCharSet(''))
        self.assertEqual('', encode_tools.findCharSet('text/html'))


    def test_findCharSet1(self):
        self.assertEqual('big5', encode_tools.findCharSet('text/html; charset=big5'))


    def test_findCharSetX(self):
        """ eXtreme findCharSet """
        self.assertEqual('big5', encode_tools.findCharSet('text/html; param1; charSET = biG5 ; param2'))


    def test_determine0(self):
        result = encode_tools.determineEncoding({}, '')
        self.assertEqual(('iso-8859-1',encode_tools.DEFAULT), result)


    def test_determine_HTTP_CONTENT_TYPE(self):
        result = encode_tools.determineEncoding(
            {'content-type': 'text/html; charset=set0' },
            '<META http-equiv="Content-Type" content="text/html; charset=big5">')
        self.assertEqual(('set0',encode_tools.HTTP_CONTENT_TYPE), result)


    def test_determine_META_CHARSET0(self):
        # does not have content-type header
        result = encode_tools.determineEncoding(
            {},
            '<META http-equiv="Content-Type" content="text/html; charset=big5">')
        self.assertEqual(('big5',encode_tools.META_CHARSET), result)


    def test_determine_META_CHARSET1(self):
        # has content-type header but without charset
        result = encode_tools.determineEncoding(
            {'content-type': 'text/html' },
            '<META http-equiv="Content-Type" content="text/html; charset=big5">')
        self.assertEqual(('big5',encode_tools.META_CHARSET), result)


    def test_determine_DEFAULT(self):
        # has content-type and meta but no charset
        result = encode_tools.determineEncoding(
            {'content-type': 'text/html' },
            '<META http-equiv="Content-Type" content="text/html">')
        self.assertEqual(('iso-8859-1',encode_tools.DEFAULT), result)


    def test_determine_lenient(self):

        result = encode_tools.determineEncoding(
            {'content-type': 'text/html; charset=bad' },
            '')
        self.assertEqual(('bad',encode_tools.HTTP_CONTENT_TYPE), result)    # controlled test

        result = encode_tools.determineEncodingLenient(
            {'content-type': 'text/html; charset=bad' },
            '')
        self.assertEqual(('iso-8859-1',encode_tools.DEFAULT), result)       # return default instead of bad


    def test_getreader(self):
        Reader = encode_tools.getreader('latin-1')
        fp = StringIO.StringIO('mam\xe1')
        reader = Reader(fp)
        udata = reader.read()
        expect = u'mam\xe1'
        self.assertEqual(udata, expect)
        self.assertEqual(type(udata), type(expect))


    def test_getreader_invalid(self):
        try:
            Reader = encode_tools.getreader('bad')
        except UnicodeError, e:
            self.assert_(e.args[0].find('bad') > 0)
        else:
            self.fail('Expect UnicodeError')



if __name__ == '__main__':
    unittest.main()