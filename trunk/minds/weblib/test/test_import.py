# -*- coding: utf-8 -*-
import StringIO
import unittest

from minds.safe_config import cfg as testcfg
from minds.weblib import store
from minds.weblib import util
from minds.weblib import import_delicious
from minds.weblib import import_netscape
from minds.weblib import import_opera
from minds.weblib import import_util

testpath = testcfg.getpath('testDoc')

class TestImport(unittest.TestCase):

    TESTFILE_PATH = testpath/'test_weblib/weblib.dat'

    def setUp(self):
        store.store_instance = store.Store()
        self.buf = StringIO.StringIO()
        store.getStore().load('*test*buffer*', self.buf)
        self.assertEqual(len(store.getWeblib().webpages),0)

    def tearDown(self):
        store.store_instance = None


    def _verify_weblib(self, isDelicious=False):
        wlib = store.getWeblib()

        # check out tags
        self.assertEqual(len(wlib.tags),5)
        self.assertTrue(wlib.tags.getByName(u'2.1-misc'))
        self.assertTrue(wlib.tags.getByName(u'4-日本語'))

        # check out webpages
        self.assertEqual(len(wlib.webpages),19)

        verified_1 = False
        verified_2 = False
        for item in wlib.webpages:
            if item.name == 'Opera Web':
                self.assertEqual(item.description, u'Type "s <search query>" in the Location Bar to perform a search on search.opera.com.')
                self.assert_(not item.tags)
                self.assertEqual(item.created, '2006-03-26')
                self.assertEqual(item.modified, '')
                verified_1 = True
            elif item.name == u'メインページ - Wikipedia':
                self.assertEqual( 'http://ja.wikipedia.org/wiki/%E3%83%A1%E3%82%A4%E3%83%B3%E3%83%9A%E3%83%BC%E3%82%B8', item.url)
                if not isDelicious: # excuse delicious which cannot export Japanese description? [2006-03-26]
                    self.assert_( '195,383' in item.description)
                self.assertEqual( item.tags, [wlib.tags.getByName(u'4-日本語')])
                self.assertEqual(item.created, '2006-03-26')
                if not isDelicious: # delicious does not have modified
                    self.assertEqual(item.modified, '2006-03-26')
                verified_2 = True
        self.assert_(verified_1 and verified_2)


    def test_netscape(self):
        fp = file(testpath/'test_import/moz_bookmarks.html','rb')
        import_netscape.import_bookmark(fp)
        self._verify_weblib()


    def test_netscape_via_safari_needed(self):
        self.fail()

    def test_netscape_via_IE_needed(self):
        self.fail()

    def test_opera(self):
        fp = file(testpath/'test_import/opera6.adr','rb')
        import_opera.import_bookmark(fp)
        self._verify_weblib()


    def test_delicious(self):
        fp = file(testpath/'test_import/delicious.xml','rb')
        import_delicious.import_bookmark(fp)
        self._verify_weblib(isDelicious=True)


class TestUtil(unittest.TestCase):

    def setUp(self):
        pass

    def test_ctime_str_2_iso8601(self):
        self.assertEqual( import_util._ctime_str_2_iso8601(''),                 '')
        self.assertEqual( import_util._ctime_str_2_iso8601('1143493822'),       '2006-03-27')   # actually 2006-3-27 13:10:22
        self.assertEqual( import_util._ctime_str_2_iso8601('1143493822.973'),   '2006-03-27')
        self.assertEqual( import_util._ctime_str_2_iso8601('today'),            '')

    def test_needed(self):
        self.fail()

if __name__ =='__main__':
    unittest.main()
