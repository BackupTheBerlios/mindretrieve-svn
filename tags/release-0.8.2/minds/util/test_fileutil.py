import StringIO
import unittest

from minds.util.fileutil import BoundedFile, RecordFile


class TestBoundedFile(unittest.TestCase):

  def test_boundedFile(self):
    print '\n@test_boundedFile'
    buf = StringIO.StringIO()
    bfp = BoundedFile(buf, 10)

    bfp.write('12345')
    self.assert_(not bfp.isOverflow())
    self.assertEqual(len(buf.getvalue()), 5)

    bfp.write('678')
    self.assert_(not bfp.isOverflow())
    self.assertEqual(len(buf.getvalue()), 8)

    bfp.write('90ab')
    self.assert_(bfp.isOverflow())
    self.assertEqual(len(buf.getvalue()), 8)

    # although bfp is still 2 characters below maxsize
    # make sure once it is overflowed you cannot write anymore
    bfp.write('c')
    self.assert_(bfp.isOverflow())
    self.assertEqual(len(buf.getvalue()), 8)


  def test_boundedFile1(self):
    print '\n@test_boundedFile1'
    buf = StringIO.StringIO()
    bfp = BoundedFile(buf, 10)

    # check boundary condition when cursize == maxsize
    bfp.write('1234567890')
    self.assert_(not bfp.isOverflow())
    self.assertEqual(len(buf.getvalue()), 10)

    bfp.write('a')
    self.assert_(bfp.isOverflow())
    self.assertEqual(len(buf.getvalue()), 10)


  def test_boundedFileDelegation(self):
    print '\n@test_boundedFileDelegation'
    buf = StringIO.StringIO()
    bfp = BoundedFile(buf, 10)

    bfp.write('1234567890')
    self.assertEqual(bfp.getvalue(), '1234567890')



class TestFileUtil(unittest.TestCase):

  def test_RecordFile(self):
    print '\n@test_RecordFile'
    f1 = StringIO.StringIO("""line1\r\nline2\r\nline3\n""")
    rec = StringIO.StringIO()
    for i, line in enumerate(RecordFile(f1,rec)):
        print 'line %d: [%s]' % (i, line)
    self.assertEqual(f1.getvalue(), rec.getvalue())



if __name__ == '__main__':
    unittest.main()