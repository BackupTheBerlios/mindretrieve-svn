"""
"""

import os, os.path, sys
import shutil
import StringIO
import unittest
import zipfile

from config_help import cfg
from minds import docarchive



def _add_documents(data):
    """ Helper to add documents.
        data is list of (id, content)
    """
    ah = docarchive.ArchiveHandler('w')
    try:
        for id, content in data:
            ah.add_document(id, StringIO.StringIO(content))
    finally:
        ah.close()



class BaseTest(unittest.TestCase):
    """ Clean up the $archive to prepare for testing """

    def setUp(self):
        self.apath = cfg.getPath('archive')
        self.cleanup()
        cfg.setupPaths()

    def cleanup(self):
        assert(self.apath == 'testdata/archive')    # avoid deleting wrong data in config goof
        shutil.rmtree(self.apath, True)



class TestDocArchive(BaseTest):

    def test_invalideId(self):

        self.assertRaises(KeyError, docarchive.parseId, '')
        self.assertRaises(KeyError, docarchive.parseId, '123a')         # non-numeric
        self.assertRaises(KeyError, docarchive.parseId, '1234567890')   # more than 9 digits
        self.assertRaises(KeyError, docarchive.parseId, 'x')


    def test_get_document(self):

        _add_documents([
            ('000000000', 'this is file 000000000'),
            ('000000002', 'this is file 000000002'),
        ])

        fp = docarchive.get_document('000000000')
        self.assertEqual(fp.read(), 'this is file 000000000')

        fp = docarchive.get_document('000000002')
        self.assertEqual(fp.read(), 'this is file 000000002')


    def test_get_document_not_exist(self):

        _add_documents([
            ('000000000', 'this is file 000000000'),
            ('000000002', 'this is file 000000002'),
        ])

        # arc_path 000000.zip exist, filename not found in arc_path
        self.assertRaises(KeyError, docarchive.get_document, '000000777')

        # arc_path 000222.zip does not exist
        self.assertRaises(KeyError, docarchive.get_document, '000222777')



class TestIdCounter(BaseTest):

    def _assertRange(self, begin, end):
        ic = docarchive.IdCounter()         # reinitialize IdCounter
        ic._findIdRange()
        self.assertEqual(ic._beginId, begin)
        self.assertEqual(ic._endId, end)



    def test_findIdRange_initial_state(self):
        self._assertRange(0,0)



    def test_findIdRange_no_file_in_zip(self):

        # 000001.zip contains no file.
        arc_path = os.path.join(self.apath, '000001.zip')
        zfile = zipfile.ZipFile(arc_path, 'w', zipfile.ZIP_DEFLATED)
        zfile.close()

        # This implementation would assume 000001+000 = 1000
        self._assertRange(1000,1001)



    def test_findIdRange(self):
        _add_documents([
            ('000000001', 'this is file 000000000'),
            ('000000002', 'this is file 000000002'),
            ('000001009', 'this is file 000001009'),
        ])
        self._assertRange(1,1010)



    def test_findIdRange_resist_garbagefile(self):
        _add_documents([
            ('000000001', 'this is file 000000000'),
            ('000000002', 'this is file 000000002'),
            ('000000099', 'this is file 000000099'),
        ])

        arc_path = os.path.join(self.apath, '000000.zip')
        zfile = zipfile.ZipFile(arc_path, 'a', zipfile.ZIP_DEFLATED)
        zfile.writestr('---', 'filename should be 3 digits')
        zfile.writestr('aaa', 'filename should be 3 digits')
        zfile.close()

        # check that zipfile is corrupted with invalid filename in it
        zfile = zipfile.ZipFile(arc_path, 'r')
        files = zfile.namelist()

        self.assertEqual(len(files), 5)
        self.assertEqual(min(files), '---')
        self.assertEqual(max(files), 'aaa')
        zfile.close()

        # _findIdRange filter out invalid filenames
        self._assertRange(1,100)



    def test_getNewId(self):

        ic = docarchive.IdCounter()         # reinitialize from fresh database

        id = ic.getNewId()
        self.assertEqual('000000000', id)
        self.assertEqual(ic._beginId, 0)
        self.assertEqual(ic._endId, 1)

        id = ic.getNewId()
        self.assertEqual('000000001', id)
        self.assertEqual(ic._beginId, 0)
        self.assertEqual(ic._endId, 2)




class TestArchiveHandler(BaseTest):

    def test_invalid_mode(self):
        self.assertRaises(ValueError, docarchive.ArchiveHandler, 'a')    # only 'r' and 'w' for mode


    def test_add_document(self):
        ah = docarchive.ArchiveHandler('w')

        # add files to archive
        ah.add_document('000000000', StringIO.StringIO('this is doc 000000000'))
        zfile, arc_path = ah.zfile, ah.arc_path

        ah.add_document('000000001', StringIO.StringIO('this is doc 000000001'))
        # assert 000000.zip remain open
        self.assert_(zfile == ah.zfile)
        self.assert_(arc_path == ah.arc_path)

        ah.add_document('000001001', StringIO.StringIO('this is doc 000001001'))
        # assert 000000.zip is switched
        self.assert_(zfile != ah.zfile)
        self.assert_(arc_path != ah.arc_path)

        ah.close()

        # check two zip files are created
        self.assert_(os.path.exists(os.path.join(self.apath, '000000.zip')))
        self.assert_(os.path.exists(os.path.join(self.apath, '000001.zip')))

        # check content
        fp = docarchive.get_document('000000001')
        self.assertEqual(fp.read(), 'this is doc 000000001')



    def test_append_to_exiting_archive(self):
        ah = docarchive.ArchiveHandler('w')

        # add files to a new archive
        ah.add_document('000000000', StringIO.StringIO('this is doc 000000000'))
        arc_path0 = ah.arc_path
        ah.close()

        # there is 1 file in the archive
        zfile = zipfile.ZipFile(arc_path0,'r')
        self.assertEqual(len(zfile.namelist()), 1)
        zfile.close()

        # append files to an exiting archive
        ah.add_document('000000001', StringIO.StringIO('this is doc 000000001'))
        arc_path = ah.arc_path
        ah.close()

        # note: there was a bug that the second add overwritten instead of append
        # Therefore added this test case catch this damaging bug

        # there are 2 files in the archive
        zfile = zipfile.ZipFile(arc_path0,'r')
        self.assertEqual(len(zfile.namelist()), 2)
        self.assertEqual(zfile.read('000'), 'this is doc 000000000')
        self.assertEqual(zfile.read('001'), 'this is doc 000000001')
        zfile.close()



if __name__ == '__main__':
    unittest.main()