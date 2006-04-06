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

def _list_names(tags):
    return ','.join(sorted(t.name for t in tags))


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
        # delicious does not support space in tag
        # delicious does not have modified
        wlib = store.getWeblib()

        # check out tags
        self.assertEqual(len(wlib.tags),5)
        if isDelicious:
            self.assertEqual(_list_names(wlib.tags), u'1-Bookmarks_Toolbar_Folder,2-Quick_Searches,2.1-misc,3-Firefox_and_Mozilla_Links,4-日本語')
        else:
            self.assertEqual(_list_names(wlib.tags), u'1-Bookmarks Toolbar Folder,2-Quick Searches,2.1-misc,3-Firefox and Mozilla Links,4-日本語')

        # check out webpages
        self.assertEqual(len(wlib.webpages),19)

        verified_1 = False
        verified_2 = False
        for item in wlib.webpages:
            if item.name == 'Opera Web':
                self.assertEqual(item.description, u'Type "s <search query>" in the Location Bar to perform a search on search.opera.com.')
                self.assertEqual(_list_names(item.tags), '')
                self.assertEqual(item.created, '2006-03-26')
                self.assertEqual(item.modified, '')
                verified_1 = True
            elif item.name == u'メインページ - Wikipedia':
                self.assertEqual( 'http://ja.wikipedia.org/wiki/%E3%83%A1%E3%82%A4%E3%83%B3%E3%83%9A%E3%83%BC%E3%82%B8', item.url)
                if not isDelicious: # excuse delicious which cannot export Japanese description? [2006-03-26]
                    self.assert_( '195,383' in item.description)
                self.assertEqual(_list_names(item.tags), u'4-日本語')
                self.assertEqual(item.created, '2006-03-26')
                if not isDelicious: # delicious does not have modified
                    self.assertEqual(item.modified, '2006-03-26')
                verified_2 = True
        self.assert_(verified_1 and verified_2)


    def _verify_weblib_ie(self):
        # IE's import/export is total mess up. Nevetheless got to test its version of export.
        # IE does not support description
        # IE export screw up non-ascii names
        wlib = store.getWeblib()

        # check out tags
        self.assertEqual(len(wlib.tags),5)
        # non-ascii folder name screwed
        self.assertEqual(_list_names(wlib.tags), u'1-Bookmarks Toolbar Folder,2-Quick Searches,2.1-misc,3-Firefox and Mozilla Links,4-???')

        # check out webpages
        self.assertEqual(len(wlib.webpages),14)     # not 19

        verified_1 = False
        verified_2 = False
        for item in wlib.webpages:
            if item.name == 'Opera Web':
              if not item.tags: # <-- HACK: there is 2 version of 'Opera Web', select the version with no tag
                import sys;print >>sys.stderr, item.tags
                self.assertEqual(_list_names(item.tags), '')
                self.assertEqual(item.created, '2006-03-27')    # HACK: IE use date of import
                self.assertEqual(item.modified, '2006-03-27')   # HACK: IE fill in modified date
                verified_1 = True
            elif item.name == u'?????? - Wikipedia':            # screwed
                self.assertEqual( 'http://ja.wikipedia.org/wiki/%E3%83%A1%E3%82%A4%E3%83%B3%E3%83%9A%E3%83%BC%E3%82%B8', item.url)
                self.assertEqual(_list_names(item.tags), u'4-???')
                self.assertEqual(item.created, '2006-03-27')    # HACK: IE use date of import
                self.assertEqual(item.modified, '2006-03-27')   # HACK: IE use date of import
                verified_2 = True
        self.assert_(verified_1 and verified_2)


    def _verify_weblib_safari(self, isDelicious=False):
        # Safari has 2 extra tags Bookmark menu and Bookmark Bar
        # Safari does not support description
        # Safari does not support dates
        wlib = store.getWeblib()

        # check out tags
        self.assertEqual(len(wlib.tags),7)
        self.assertEqual(_list_names(wlib.tags), u'1-Bookmarks Toolbar Folder,2-Quick Searches,2.1-misc,3-Firefox and Mozilla Links,4-日本語,Bookmarks Bar,Bookmarks Menu')

        # check out webpages
        self.assertEqual(len(wlib.webpages),19)

        verified_1 = False
        verified_2 = False
        for item in wlib.webpages:
            if item.name == 'Opera Web':
                self.assertEqual(_list_names(item.tags), 'Bookmarks Menu')
                verified_1 = True
            elif item.name == u'メインページ - Wikipedia':
                self.assertEqual( 'http://ja.wikipedia.org/wiki/%E3%83%A1%E3%82%A4%E3%83%B3%E3%83%9A%E3%83%BC%E3%82%B8', item.url)
                self.assertEqual( _list_names(item.tags), u'4-日本語,Bookmarks Menu')
                verified_2 = True
        self.assert_(verified_1 and verified_2)


    def test_netscape_bad(self):
        fp = file(testpath/'test_magic/penguin100.jpg','rb')    # jpg bomb
        import_netscape.import_bookmark(fp)

        # not harm done. nothing imported
        wlib = store.getWeblib()
        self.assertEqual(len(wlib.tags),0)
        self.assertEqual(len(wlib.webpages),0)


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


    def test_opera_bad(self):
        fp = file(testpath/'test_magic/penguin100.jpg','rb')    # jpg bomb
        import_opera.import_bookmark(fp)

        # not harm done. nothing imported
        wlib = store.getWeblib()
        self.assertEqual(len(wlib.tags),0)
        self.assertEqual(len(wlib.webpages),0)


    def test_delicious(self):
        fp = file(testpath/'test_import/delicious.xml','rb')
        import_delicious.import_bookmark(fp)
        self._verify_weblib(isDelicious=True)


    def test_delicious_bad(self):
        fp = file(testpath/'test_magic/penguin100.jpg','rb')    # jpg bomb
        import_delicious.import_bookmark(fp)

        # not harm done. nothing imported
        wlib = store.getWeblib()
        self.assertEqual(len(wlib.tags),0)
        self.assertEqual(len(wlib.webpages),0)


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
        self.assertEqual(_list_names(wlib.tags), 'f1,f11,f2,f22')
        webpages = sorted(t.name for t in wlib.webpages)
        self.assertEqual(_list_names(wlib.webpages), 'b01,b02,b03,b04')

        # verify b01
        w = [w for w in wlib.webpages if w.name=='b01'][0]
        self.assertEqual(w.name,          'b01')
        self.assertEqual(w.url,           'http://b01/')
        self.assertEqual(w.description,   'd01')
        self.assertEqual(w.created,       '2006-01-01')
        self.assertEqual(w.modified,      '2006-01-02')
        self.assertEqual(_list_names(w.tags),'f1')

        # verify b03
        w = [w for w in wlib.webpages if w.name=='b03'][0]
        self.assertEqual(w.description, 'd03')
        self.assertEqual(_list_names(w.tags), 'f1,f11')

        # verify b04
        w = [w for w in wlib.webpages if w.name=='b04'][0]
        self.assertEqual(w.description, 'd04')
        self.assertEqual(_list_names(w.tags), '')


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
        self.assertEqual(_list_names(wlib.tags), 't1,t2,t3')
        self.assertEqual(_list_names(wlib.webpages), 'b01,b02,b03,b04')

        # verify b01
        w = [w for w in wlib.webpages if w.name=='b01'][0]
        self.assertEqual(w.name,          'b01')
        self.assertEqual(w.url,           'http://b01/')
        self.assertEqual(w.description,   'd01')
        self.assertEqual(w.created,       '2006-01-01')
        self.assertEqual(w.modified,      '2006-01-02')
        self.assertEqual(_list_names(w.tags),'')

        # verify b04
        w = [w for w in wlib.webpages if w.name=='b04'][0]
        self.assertEqual(w.name,          'b04')
        self.assertEqual(w.url,           'http://b04/')
        self.assertEqual(w.description,   'd04')
        self.assertEqual(w.created,       '2006-01-01')
        self.assertEqual(w.modified,      '2006-01-02')
        self.assertEqual(_list_names(w.tags),'t1,t2,t3')


    def test_ctime_str_2_iso8601(self):
        self.assertEqual( import_util._ctime_str_2_iso8601(''),                 '')
        self.assertEqual( import_util._ctime_str_2_iso8601('1143493822'),       '2006-03-27')   # actually 2006-3-27 13:10:22
        self.assertEqual( import_util._ctime_str_2_iso8601('1143493822.973'),   '2006-03-27')
        self.assertEqual( import_util._ctime_str_2_iso8601('today'),            '')


    def test_import_netscape_PushBackIterator(self):
        it = import_netscape.PushBackIterator(iter([1,2,3]))
        self.assertEqual(it.next(), 1)
        self.assertEqual(it.next(), 2)
        it.push_back(2)
        self.assertEqual(it.next(), 2)
        self.assertEqual(it.next(), 3)
        it.push_back(3)
        self.assertEqual(it.next(), 3)
        self.assertRaises(StopIteration, it.next)



if __name__ =='__main__':
    unittest.main()
