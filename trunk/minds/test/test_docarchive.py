"""
"""

import os, os.path, sys
import shutil
import StringIO
import unittest

from config_help import cfg
from minds import docarchive



class TestDocArchive(unittest.TestCase):

    def setUp(self):
        self.cleanup()
        cfg.setupPaths()


    def cleanup(self):
        # hardcode test directory to be removed to avoid deleting real data in config goof
        shutil.rmtree('testdata/archive', True)


    def test_invalideId(self):
        da = docarchive.docarc

        self.assertRaises(ValueError, da.get_archive, '')
        self.assertRaises(ValueError, da.get_archive, '123a')       # non-numeric
        self.assertRaises(ValueError, da.get_archive, '1234567890') # more than 9 digits

        self.assertRaises(ValueError, da.get_archive, 'x')
        self.assertRaises(ValueError, da.get_document, None, 'x')
        self.assertRaises(ValueError, da.add_document, None, 'x', None)


    def test_getNewId(self):
        da = docarchive.DocArchive()        # reinitialize DocArchive
        id = da.getNewId()                  # test getNewId() in fresh database
        self.assertEqual('000000001', id)


    def test_add_and_get(self):
        da = docarchive.docarc

        # add documents
        id = '000000123'
        arc = da.get_archive(id)
        self.assert_(arc)                       # simple get_archive() test
        da.add_document(arc, id, StringIO.StringIO('this is a test document1'))


        id = '000000124'
        arc0 = arc
        arc = da.get_archive(id, arc0, True)
        self.assert_(arc0 is arc)               # test reuse of arc in get_archive()
        da.add_document(arc, id, StringIO.StringIO('this is a test document2'))


        id = '000001124'
        arc0 = arc
        arc = da.get_archive(id, arc0, True)
        self.assertNotEqual(arc0, arc)          # test new arc being opened
        da.add_document(arc, id, StringIO.StringIO('this is a test document3'))


        # try to write to arc0 to make sure get_archive() has closed it for us
        self.assertRaises(Exception, arc0.writestr, 'dummy', 'dummy data')


        # test error reinserting to existing id
        self.assertRaises(KeyError, da.add_document, arc, id, StringIO.StringIO('this is a test document3'))

        arc.close()


        # get documents
        id = '000000123'
        arc, fp = da.get_arc_document(id)       # simple get_arc_document() test
        self.assertEqual('this is a test document1', fp.read())

        id = '000000124'
        fp = da.get_document(arc, id)           # simple get_document() test
        self.assertEqual('this is a test document2', fp.read())

        id = '000000125'                        # test doc not found in get_document()
        self.assertRaises(KeyError, da.get_document, arc, id)

        arc.close()

        id = '000001125'                        # test doc not found in get_arc_document()
        self.assertRaises(KeyError, da.get_arc_document, id)


        # test getNewId()
        self.assertEqual(None, da.currentId)    # currentId are still uninitialized

        id = da.getNewId()
        self.assertEqual('000001125', id)       # this will trigger lazy initialization

        id = da.getNewId()
        self.assertEqual('000001126', id)



if __name__ == '__main__':
    unittest.main()