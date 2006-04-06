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

Folder = import_util.Folder
Bookmark = import_util.Bookmark

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


    def _verify_weblib_ie(self):
        # IE's import/export is total mess up. Nevetheless got to test its version of export.
        wlib = store.getWeblib()

        # check out tags
        self.assertEqual(len(wlib.tags),5)
        self.assertTrue(wlib.tags.getByName(u'2.1-misc'))
        self.assertTrue(wlib.tags.getByName(u'4-???'))          # screwed

        # check out webpages
        self.assertEqual(len(wlib.webpages),14)     # not 19

        verified_1 = False
        verified_2 = False
        for item in wlib.webpages:
            if item.name == 'Opera Web':
              if not item.tags: # <-- HACK: there is 2 version of 'Opera Web', select the version with no tag
                # IE have no description
                #self.assertEqual(item.description, u'Type "s <search query>" in the Location Bar to perform a search on search.opera.com.')
                import sys;print >>sys.stderr, item.tags
                self.assert_(not item.tags)
                self.assertEqual(item.created, '2006-03-27')    # HACK: IE use date of import
                self.assertEqual(item.modified, '2006-03-27')   # HACK: IE fill in modified date
                verified_1 = True
            elif item.name == u'?????? - Wikipedia':            # screwed
                self.assertEqual( 'http://ja.wikipedia.org/wiki/%E3%83%A1%E3%82%A4%E3%83%B3%E3%83%9A%E3%83%BC%E3%82%B8', item.url)
                # IE have no description
                #if not isDelicious: # excuse delicious which cannot export Japanese description? [2006-03-26]
                #    self.assert_( '195,383' in item.description)
                self.assertEqual( item.tags, [wlib.tags.getByName(u'4-???')])   # screwed
                self.assertEqual(item.created, '2006-03-27')    # HACK: IE use date of import
                self.assertEqual(item.modified, '2006-03-27')   # HACK: IE use date of import
                verified_2 = True
        self.assert_(verified_1 and verified_2)


    def _verify_weblib_safari(self, isDelicious=False):
        wlib = store.getWeblib()

        # check out tags
#        self.assertEqual(len(wlib.tags),5)
#        self.assertTrue(wlib.tags.getByName(u'2.1-misc'))
#        self.assertTrue(wlib.tags.getByName(u'4-日本語'))

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


    def test_netscape_via_safari(self):
        fp = file(testpath/'test_import/Safari Bookmarks.html','rb')
        import_netscape.import_bookmark(fp)
        self._verify_weblib_safari()


    def test_netscape_via_IE(self):
        fp = file(testpath/'test_import/ie_bookmark.htm','rb')
        import_netscape.import_bookmark(fp)
        self._verify_weblib_ie()


    def test_opera(self):
        fp = file(testpath/'test_import/opera6.adr','rb')
        import_opera.import_bookmark(fp)
        self._verify_weblib()


    def test_delicious(self):
        fp = file(testpath/'test_import/delicious.xml','rb')
        import_delicious.import_bookmark(fp)
        self._verify_weblib(isDelicious=True)


class TestImportUtil(unittest.TestCase):

    TESTFILE_PATH = testpath/'test_weblib/weblib.dat'

    def setUp(self):
        store.store_instance = store.Store()
        self.buf = StringIO.StringIO()
        store.getStore().load('*test*buffer*', self.buf)
        self.assertEqual(len(store.getWeblib().webpages),0)

    def tearDown(self):
        store.store_instance = None

    def test_import_tree(self):
        # import 4 test bookmarks
        root = Folder('', [
            Folder('f1', [
                Bookmark('b01', 'http://b01/', 'd01', '2006-01-01', '2006-01-02'),
                Bookmark('b02', 'http://b02/', 'd02', '2006-01-01', '2006-01-02'),
                Folder('f11', [
                    Bookmark('b03', 'http://b03/', 'd03', '2006-01-01', '2006-01-02'),
                ]),
            ]),
            Folder('f2', [
                Folder('f22', []),
            ]),
            Bookmark('b04', 'http://b04/', 'd04', '2006-01-01', '2006-01-02'),
        ])
        import_util.import_tree(root)

        # verify 4 tags and 4 pages
        wlib = store.getWeblib()
        tags = sorted(t.name for t in wlib.tags)
        self.assertEqual(','.join(tags), 'f1,f11,f2,f22')
        webpages = sorted(t.name for t in wlib.webpages)
        self.assertEqual(','.join(webpages), 'b01,b02,b03,b04')

        # verify b01
        w = [w for w in wlib.webpages if w.name=='b01'][0]
        tags = ','.join(sorted(t.name for t in w.tags))
        self.assertEqual(w.name,          'b01')
        self.assertEqual(w.url,           'http://b01/')
        self.assertEqual(w.description,   'd01')
        self.assertEqual(w.created,       '2006-01-01')
        self.assertEqual(w.modified,      '2006-01-02')
        self.assertEqual(tags,            'f1')

        # verify b03
        w = [w for w in wlib.webpages if w.name=='b03'][0]
        tags = ','.join(sorted(t.name for t in w.tags))
        self.assertEqual(w.description,   'd03')
        self.assertEqual(tags,            'f1,f11')

        # verify b04
        w = [w for w in wlib.webpages if w.name=='b04'][0]
        tags = ','.join(sorted(t.name for t in w.tags))
        self.assertEqual(w.description,   'd04')
        self.assertEqual(tags,            '')



    def test_import_bookmarks(self):
        # import 4 test bookmarks
        data = [
            (Bookmark('b01', 'http://b01/', 'd01', '2006-01-01', '2006-01-02'), ''),
            (Bookmark('b02', 'http://b02/', 'd02', '2006-01-01', '2006-01-02'), 't1'),
            (Bookmark('b03', 'http://b03/', 'd03', '2006-01-01', '2006-01-02'), 't2,t3'),
            (Bookmark('b04', 'http://b04/', 'd04', '2006-01-01', '2006-01-02'), 't1,t2,t3'),
        ]
        for b, tags in data:
            b.tags = tags
        bookmarks = [b for b, tags in data]
        import_util.import_bookmarks(bookmarks)

        # verify 3 tags and 4 pages
        wlib = store.getWeblib()
        tags = sorted(t.name for t in wlib.tags)
        self.assertEqual(','.join(tags), 't1,t2,t3')
        webpages = sorted(t.name for t in wlib.webpages)
        self.assertEqual(','.join(webpages), 'b01,b02,b03,b04')

        # verify b01
        w = [w for w in wlib.webpages if w.name=='b01'][0]
        tags = ','.join(sorted(t.name for t in w.tags))
        self.assertEqual(w.name,          'b01')
        self.assertEqual(w.url,           'http://b01/')
        self.assertEqual(w.description,   'd01')
        self.assertEqual(w.created,       '2006-01-01')
        self.assertEqual(w.modified,      '2006-01-02')
        self.assertEqual(tags,            '')

        # verify b04
        w = [w for w in wlib.webpages if w.name=='b04'][0]
        tags = ','.join(sorted(t.name for t in w.tags))
        self.assertEqual(w.name,          'b04')
        self.assertEqual(w.url,           'http://b04/')
        self.assertEqual(w.description,   'd04')
        self.assertEqual(w.created,       '2006-01-01')
        self.assertEqual(w.modified,      '2006-01-02')
        self.assertEqual(tags,            't1,t2,t3')


    def test_ctime_str_2_iso8601(self):
        self.assertEqual( import_util._ctime_str_2_iso8601(''),                 '')
        self.assertEqual( import_util._ctime_str_2_iso8601('1143493822'),       '2006-03-27')   # actually 2006-3-27 13:10:22
        self.assertEqual( import_util._ctime_str_2_iso8601('1143493822.973'),   '2006-03-27')
        self.assertEqual( import_util._ctime_str_2_iso8601('today'),            '')


if __name__ =='__main__':
    unittest.main()
