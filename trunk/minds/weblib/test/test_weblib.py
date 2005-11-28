# -*- coding: utf-8 -*-
import datetime
import sets
import StringIO
import sys
import unittest

from minds.safe_config import cfg as testcfg
from minds import weblib
from minds.weblib import store

testpath = testcfg.getpath('testDoc')


class TestWeblib(unittest.TestCase):

    TESTFILE_PATH = testpath/'test_weblib/weblib.dat'

    def setUp(self):
        self.store = store.Store()
        self.buf = StringIO.StringIO()
        self.store.load('*test*buffer*', self.buf)


    def tearDown(self):
        pass


    def _make_test_data(self):
        store = self.store
        wlib = store.wlib
        store.writeTag(weblib.Tag(name='def_tag1'))
        store.writeTag(weblib.Tag(name='def_tag2'))
        store.writeTag(weblib.Tag(name='def_tag3'))
        self.assertEqual(wlib.tags.getById(1).name, 'def_tag1')
        store.writeWebPage(weblib.WebPage(name='def_page1'))
        store.writeWebPage(weblib.WebPage(name='def_page2'))
        store.writeWebPage(weblib.WebPage(name='def_page3'))
        self.assertEqual(wlib.webpages.getById(1).name, 'def_page1')
        self.assertEqual((3, 3), (len(wlib.tags), len(wlib.webpages)))


    def _load_TESTFILE(self):
        self.TESTTEXT = file(self.TESTFILE_PATH,'rb').read()
        self.buf = StringIO.StringIO(self.TESTTEXT)
        self.store.load('*test*weblib*', self.buf)


    def _assert_weblib_size(self, nt, nw):
        self.assertEqual(len(self.store.wlib.tags), nt)
        self.assertEqual(len(self.store.wlib.webpages), nw)


    def test_default_tag(self):
        wlib = self.store.wlib

        # brand new wlib, no tag exists
        self.assertEqual(len(wlib.tags), 0)

        # getDefaultTag the first time will make a tag
        tag = wlib.getDefaultTag()
        self.assertTrue(tag)
        self.assertEqual(tag, wlib.tags.getByName(tag.name))
        self.assertEqual(len(wlib.tags), 1)

        # defaultTag already exist, will use a different code path
        tag2 = wlib.getDefaultTag()
        self.assertEqual(tag, tag2)
        self.assertEqual(len(wlib.tags), 1)


    def test_tag_rename(self):
        self._load_TESTFILE()
        wlib = self.store.wlib

        # originally
        self.assertTrue(wlib.tags.getByName('English'))
        self.assertTrue('English' in wlib.category.getDescription())

        wlib.tag_rename(wlib.tags.getByName('English'), 'Irish')

        # after
        self.assertTrue(not wlib.tags.getByName('English'))
        self.assertTrue('English' not in wlib.category.getDescription())
        self.assertTrue(wlib.tags.getByName('Irish'))
        self.assertTrue('Irish' in wlib.category.getDescription())


    def test_tag_merge_del(self):
        self._load_TESTFILE()
        wlib = self.store.wlib

        # before
        item = wlib.webpages.getById(5)
        et = wlib.tags.getByName(u'English')
        ft = wlib.tags.getByName(u'Français')
        kt = wlib.tags.getByName(u'Kremlin')
        self.assertTrue(et and ft and kt)
        # item 5 has English & Kremlin
        self.assertEqual(len(item.tags), 2)
        self.assertTrue(kt in item.tags)
        self.assertTrue(et in item.tags)
        # state of wlib
        self.assertEqual(len(wlib.tags), 6)
        self.assertTrue(u'English' in wlib.category.getDescription())
        self.assertTrue(u'Français' in wlib.category.getDescription())
        self.assertTrue(u'Kremlin' in wlib.category.getDescription())

        # 1. rename English to a new tag Français
        wlib.tag_merge_del(et, ft)

        item = wlib.webpages.getById(5)
        self.assertEqual(len(item.tags), 2)
        self.assertTrue(kt in item.tags)
        self.assertTrue(ft in item.tags)
        self.assertTrue(et not in item.tags)
        self.assertEqual(len(wlib.tags), 5)
        self.assertTrue(u'English' not in wlib.category.getDescription())

        # 2. rename Kremlin to an existing tag Français (merge)
        wlib.tag_merge_del(kt, ft)

        item = wlib.webpages.getById(5)
        self.assertEqual(len(item.tags), 1)
        self.assertTrue(ft in item.tags)
        self.assertEqual(len(wlib.tags), 4)
        self.assertTrue(u'Kremlin' not in wlib.category.getDescription())

        # 3. rename Français to nothing (delete)
        wlib.tag_merge_del(ft)

        item = wlib.webpages.getById(5)
        self.assertEqual(len(item.tags), 0)
        self.assertEqual(len(wlib.tags), 3)
        self.assertTrue(u'Français' not in wlib.category.getDescription())


    def test_setCategoryCollapse(self):
        self._load_TESTFILE()
        wlib = self.store.wlib

        tid = wlib.tags.getByName('English').id
        isCC = lambda: 'c' in wlib.tags.getByName('English').flags

        self.assertTrue(not isCC())

        wlib.setCategoryCollapse(tid, True)
        self.assertTrue(isCC())

        wlib.setCategoryCollapse(tid, False)
        self.assertTrue(not isCC())


    def test_visit(self):
        self._load_TESTFILE()
        wlib = self.store.wlib

        today = datetime.date.today().isoformat()
        # before
        item = wlib.webpages.getById(5)
        self.assertTrue(item.lastused < today)  # test data supposed to have a date in the past

        # visit
        item = wlib.visit(item)

        # after
        item = wlib.webpages.getById(5)
        self.assertTrue(item.lastused >= today)


    def test_editTags(self):
        self._load_TESTFILE()
        wlib = self.store.wlib

        itag = wlib.tags.getByName('inbox')
        ktag = wlib.tags.getByName('Kremlin')

        # before
        for id in range(2,6):
            page = wlib.webpages.getById(id)
            self.assertTrue(itag not in page.tags)
            self.assertTrue(ktag in page.tags)

        # editTags
        webpages = [wlib.webpages.getById(id) for id in range(2,6)]
        wlib.editTags(webpages, [], [itag], [ktag])

        # after
        for id in range(2,6):
            page = wlib.webpages.getById(id)
            self.assertTrue(itag in page.tags)
            self.assertTrue(ktag not in page.tags)


    def test_compile(self):
        self.fail('need test')


if __name__ == '__main__':
    unittest.main()
