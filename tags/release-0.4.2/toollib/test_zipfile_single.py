import StringIO
import sys
import unittest
import zipfile

from toollib import zipfile_single


class TestZipFileSingle(unittest.TestCase):

    def setUp(self):
        self.fp = StringIO.StringIO()

        # create a sample zip file in self.fp
        zf = zipfile.ZipFile(self.fp,'w')
        zf.writestr('f1',       'this is f1')
        zf.writestr('f2',       'this is f2')
        zf.writestr('d1/f1',    'this is d1/f1')
        zf.writestr('d1/d2/f1', 'this is d1/d2/f1')
        zf.close()


    def test_zipfile_single(self):

        zf = zipfile_single.ZipFile(self.fp, 'r')

        # verify that zipfile_single can read content of the zipfile
        self.assertEqual(zf.read('f1'),       'this is f1'      )
        self.assertEqual(zf.read('f2'),       'this is f2'      )
        self.assertEqual(zf.read('d1/f1'),    'this is d1/f1'   )
        self.assertEqual(zf.read('d1/d2/f1'), 'this is d1/d2/f1')
        zf.close()


    def test_match_zipfile(self):

        zf = zipfile_single.ZipFile(self.fp, 'r')
        zf0 = zipfile_single.ZipFile(StringIO.StringIO(self.fp.getvalue()), 'r')

        # verify that zipfile_single's content match zipfile's
        self.assertEqual(zf0.read('f1'),       zf.read('f1')      )
        self.assertEqual(zf0.read('f2'),       zf.read('f2')      )
        self.assertEqual(zf0.read('d1/f1'),    zf.read('d1/f1')   )
        self.assertEqual(zf0.read('d1/d2/f1'), zf.read('d1/d2/f1'))

        zf.close()
        zf0.close()


    def test_not_exist(self):

        zf = zipfile_single.ZipFile(self.fp, 'r')
        self.assertRaises(KeyError, zf.read, 'notexist')



if __name__ == '__main__':
    unittest.main()