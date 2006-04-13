import StringIO
import unittest

from minds.safe_config import cfg as testcfg
from minds.util import fileutil
from minds.util.fileutil import BoundedFile, RecordFile

testpath = testcfg.getpath('data')
assert 'test' in testpath

class TestBoundedFile(unittest.TestCase):

  def test_boundedFile(self):
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
    buf = StringIO.StringIO()
    bfp = BoundedFile(buf, 10)

    bfp.write('1234567890')
    self.assertEqual(bfp.getvalue(), '1234567890')



class TestFileUtil(unittest.TestCase):

  def test_RecordFile(self):
    f1 = StringIO.StringIO("""line1\r\nline2\r\nline3\n""")
    rec = StringIO.StringIO()
    for i, line in enumerate(RecordFile(f1,rec)):
        print 'line %d: [%s]' % (i, line)
    self.assertEqual(f1.getvalue(), rec.getvalue())


  def test_shift_files(self):
    A = testpath / 'a'
    B = testpath / 'b'
    C = testpath / 'c'
    if A.exists(): A.remove()
    if B.exists(): B.remove()
    if C.exists(): C.remove()

    # -- test 0 ------------------------------------------------------------------------
    # ok if non of them exist
    fileutil.shift_files([A,B,C])

    self.assert_(not A.exists())
    self.assert_(not B.exists())
    self.assert_(not C.exists())

    # -- test 1 ------------------------------------------------------------------------
    file(A,'w').write('1')

    # A->B (new file)
    fileutil.shift_files([A,B])

    self.assert_(not A.exists())
    self.assertEqual(file(B).read(), '1')

    # -- test 2 ------------------------------------------------------------------------
    file(A,'w').write('2')

    # A->B (existing file)
    fileutil.shift_files([A,B])

    self.assert_(not A.exists())
    self.assertEqual(file(B).read(), '2')

    # -- test 3 ------------------------------------------------------------------------
    file(A,'w').write('3')

    # A->B->C (new file)
    fileutil.shift_files([A,B,C])

    self.assert_(not A.exists())
    self.assertEqual(file(B).read(), '3')
    self.assertEqual(file(C).read(), '2')

    # -- test 4 ------------------------------------------------------------------------
    file(A,'w').write('4')

    # A->B->C (existing file)
    fileutil.shift_files([A,B,C])

    self.assert_(not A.exists())
    self.assertEqual(file(B).read(), '4')
    self.assertEqual(file(C).read(), '3')

    # -- test 5 ------------------------------------------------------------------------
    file(A,'w').write('5')

    # A->xBx->C (existing file)
    B.remove()
    fileutil.shift_files([A,B,C])

    self.assert_(not A.exists())
    self.assertEqual(file(B).read(), '5')
    self.assert_(not C.exists())


if __name__ == '__main__':
    unittest.main()