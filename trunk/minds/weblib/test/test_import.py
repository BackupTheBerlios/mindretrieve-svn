# -*- coding: utf-8 -*-
import StringIO
import unittest

from minds.safe_config import cfg as testcfg
from minds.weblib import store
from minds.weblib import util
from minds.weblib import import_netscape
from minds.weblib import import_opera
from minds.weblib import import_delicious

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
        self.assertTrue(wlib.tags.getByName('2.1-misc'))
        self.assertTrue(wlib.tags.getByName(u'4-日本語'))

        # check out webpages
        self.assertEqual(len(wlib.webpages),19)

        # check out the 'Opera support' entry
        self.assertTrue( 'Type "o <search query>"' in \
            '|'.join([item.description for item in wlib.webpages]))

        # check out the http://ja.wikipedia.org entry
        self.assertTrue( u'メインページ - Wikipedia' in [item.name for item in wlib.webpages])
        self.assertTrue( 'http://ja.wikipedia.org/wiki/%E3%83%A1%E3%82%A4%E3%83%B3%E3%83%9A%E3%83%BC%E3%82%B8' in \
            [item.url for item in wlib.webpages])

        if not isDelicious:
            # excuse delicious which cannot export Japanese description? [2006-03-26]
            self.assertTrue( '195,383' in \
                '|'.join([item.description for item in wlib.webpages]))


    def test_netscape_needed(self):
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

    def test_needed(self):
        self.fail()


if __name__ =='__main__':
    unittest.main()
