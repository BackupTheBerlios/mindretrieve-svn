import httplib
import StringIO
import sys
import unittest

import patterns_tester
import rspreader

testdir = 'lib/testdocs/'
TESTPATH = testdir+'creative_commons.qlog'


def readAll(fp):
    """ fp.read() return data in trunk. This method read the entire output in one piece. """
    lst = []
    while True:
        data = fp.read()
        if not data:
            break
        lst.append(data)
    return ''.join(lst)


class BaseTester(unittest.TestCase):
  """ Helper base class """
  def setUp(self):
    self.fp = None
  def tearDown(self):
    if self.fp: self.fp.close()


class TestRspReader(BaseTester):

  def test_RspReader_controlled(self):
    """ controlled test of test_RspReader() without using RspReader """
    self.fp = file(TESTPATH, 'rb')
    p = patterns_tester.checkPatterns(readAll(self.fp), [' HTTP/1.0'])    # request line found
    self.assertEqual(None, p)


  def test_RspReader(self):
    self.fp = rspreader.RspReader(file(TESTPATH, 'rb'), TESTPATH)
    p = patterns_tester.checkPatterns(readAll(self.fp), [' HTTP/1.0'])    # request line not found
    self.assertEqual(' HTTP/1.0', p)

    # seek(0) doesn't work for RspReader, reopen
    self.fp.close()

    self.fp = rspreader.RspReader(file(TESTPATH, 'rb'), TESTPATH)
    p = patterns_tester.checkPatterns(readAll(self.fp), [
        ' 200 OK', 'Content-Length: ', '\r\n',              # response found
        '<!DOCTYPE html', '<html', '</body>', '</html>',    # content found
        ], '<'
    )
    self.assertEqual(None, p)



class TestChunked(BaseTester):

  def _assertError(self, data, msg):
    try:
        rspreader.readChunked(StringIO.StringIO(data))
        self.fail('Expect error')
    except IOError, e:
        if str(e).find(msg) < 0:
            self.fail('Expect error "%s"; received "%s"' % (msg, e))


  def test0(self):
    self._assertError('', 'Unexpected EOF')


  def testNoLength(self):
    self._assertError('\r\n', 'Invalid chunk length')


  def testBadLength(self):
    self._assertError('*\r\n', 'Invalid chunk length')


  def testNegativeLength(self):
    self._assertError('-1\r\n', 'Invalid chunk length')


  def testIncompleteChunk(self):
    self._assertError('5\r\nabc', 'EOF before reading chunk of ')


  def testInvalidEOC(self):
    self._assertError('5\r\nabcde0\r\n', 'Invalid end of chunk')


  def testErrorOnSecondBlock(self):
    self._assertError('5\r\nabcde\r\n', 'Unexpected EOF')


  def testEmpty(self):
    buf = StringIO.StringIO('0\r\n')
    fp = rspreader.readChunked(buf)
    self.assertEqual('', readAll(fp))


  def testOneBlock(self):
    buf = StringIO.StringIO('5\r\nabcde\r\n0\r\n')
    fp = rspreader.readChunked(buf)
    self.assertEqual('abcde', readAll(fp))


  def testTwoBlocks(self):
    buf = StringIO.StringIO('5\r\nabcde\r\n1\r\n\n\r\n0\r\n')   # second block is a single \n
    fp = rspreader.readChunked(buf)
    self.assertEqual('abcde\n', readAll(fp))



class TestContentReader(BaseTester):

  def test0(self):
    fp = StringIO.StringIO('')
    self.assertRaises(IOError, rspreader.ContentReader, fp, 'null')


  def test_empty_response(self):
    self.fp = file(testdir + 'empty_response.mlog', 'rb')
    self.assertRaises(httplib.BadStatusLine, rspreader.ContentReader, self.fp, 'empty_response.mlog')


  def test_gzip_encoding(self):
    self.fp = file(testdir + 'gzipped(slashdot).mlog', 'rb')
    rfile = rspreader.ContentReader(self.fp, 'gzipped(slashdot).mlog')
    p = patterns_tester.checkPatterns(readAll(rfile), [
        '<!DOCTYPE',
        'Slashdot: News for nerds, stuff that matters',
        '<!-- Advertisement code. -->',
        '</HTML>'
        ], '<'
    )
    self.assertEqual(None, p)


  def test_no_encoding_controlled(self):
    """ controlled test of test_no_encoding() without using ContentReader"""
    self.fp = file(TESTPATH, 'rb')
    p = patterns_tester.checkPatterns(self.fp.read(), [' HTTP/1.0'])   # request line found
    self.assertEqual(None, p)


  def test_no_encoding(self):
    self.fp = file(TESTPATH, 'rb')
    rfile = rspreader.ContentReader(self.fp, TESTPATH)
    p = patterns_tester.checkPatterns(readAll(rfile), [' HTTP/1.0'])     # request line not found
    self.assertEqual(' HTTP/1.0', p)
    rfile.seek(0)

    p = patterns_tester.checkPatterns(readAll(rfile), [' 200 '])         # response header not included
    self.assertEqual(' 200 ', p)
    rfile.seek(0)

    p = patterns_tester.checkPatterns(readAll(rfile),
        ['<!DOCTYPE html', '<html', '</body>', '</html>',],
        '<'
    )
    self.assertEqual(None, p)


  def testChunked(self):
    self.fp = file(testdir + 'chunked(ucsc).mlog', 'rb')
    rfile = rspreader.ContentReader(self.fp, 'chunked(ucsc).mlog')
    p = patterns_tester.checkPatterns(readAll(rfile), [
        '<HTML>',
        '<TITLE>MEMORANDUM</TITLE>\n',
        'positions 7 through 12.',              # this sentence span chunks
        '</HTML>'
        ], '<'
    )
    self.assertEqual(None, p)


  def testChunkedGzip(self):
    self.fp = file(testdir + 'chunked-gzip(BBR).mlog', 'rb')
    rfile = rspreader.ContentReader(self.fp, 'chunked-gzip(BBR).mlog')
    p = patterns_tester.checkPatterns(readAll(rfile), [
        '<HTML>',
        'google_ad_client = "pub-5216754536572039";\n',
        '</HTML>'
        ], '<'
    )
    self.assertEqual(None, p)


  def test_deflate(self):
    self.fp = file(testdir + 'deflate(safari).qlog', 'rb')
    try:
        rfile = rspreader.ContentReader( self.fp, 'deflate(safari).qlog')
        self.fail('Expect IOError')
    except IOError, e:
        if 'deflate' not in str(e):
            self.fail('Expect deflate encoding error, gets: %s' % e)



class TestOpen(BaseTester):

  def testOpenMlog_controlled(self):
    self.fp = file(TESTPATH, 'rb')
    p = patterns_tester.checkPatterns(self.fp.read(), [
        ' HTTP/1.0',     # request found
        ' 200 OK',       # response found
    ])
    self.assertEqual(None, p)


  def testOpenMlog(self):
    self.fp = rspreader.openlog(TESTPATH)

    p = patterns_tester.checkPatterns(readAll(self.fp), [' HTTP/1.0']) # request not found
    self.assertEqual(' HTTP/1.0', p)
    self.fp.seek(0)

    p = patterns_tester.checkPatterns(readAll(self.fp), [' 200 OK'])   # response not found
    self.assertEqual(' 200 OK', p)
    self.fp.seek(0)

    p = patterns_tester.checkPatterns(readAll(self.fp),
        ['<!DOCTYPE html', '<html', '</body>', '</html>',],
        '<'
    )
    self.assertEqual(None, p)


  def testOpenMlogBinary(self):
    self.fp = rspreader.openlog(testdir + 'gif.qlog')
    self.assertEqual('GIF89a', self.fp.read(6))


  def testOpenRegularDoc(self):
    self.fp = file(testdir + 'basictags.html', 'rb')
    p = patterns_tester.checkPatterns(self.fp.read(), [
        '<html>',
        '<h1>h1-Sample',
        '</html>',
        ], 'x'
    )
    self.assertEqual(None, p)



if __name__ == '__main__':
    unittest.main()