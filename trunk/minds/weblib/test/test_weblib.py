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

class TestTag(unittest.TestCase):

    def test0(self):
        # empty name not allowed
        self.assertRaises(ValueError, weblib.Tag, name='')

    def test_hasIllegalChar(self):
        illegal = ',@#+:'
        self.assert_(weblib.Tag.hasIllegalChar(illegal))
        self.assert_(weblib.Tag.hasIllegalChar('filler,'))
        self.assert_(weblib.Tag.hasIllegalChar('filler@'))
        self.assert_(weblib.Tag.hasIllegalChar('filler#'))
        self.assert_(weblib.Tag.hasIllegalChar('filler+'))
        self.assert_(weblib.Tag.hasIllegalChar('filler:'))

        xascii = r""" !"$%&'()*-./0123456789;<=>?ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~""" + '\x7f'
        self.failIf(weblib.Tag.hasIllegalChar(xascii))

        # covered all printable ascii?
        self.assertEqual(len(illegal)+len(xascii), 96)

    def test_cleanIllegalChar(self):
        illegal = ',@#+:'
        self.assertEqual(weblib.Tag.cleanIllegalChar(illegal)  , '?????')
        self.assertEqual(weblib.Tag.cleanIllegalChar('filler,'), 'filler?')
        self.assertEqual(weblib.Tag.cleanIllegalChar('filler@'), 'filler?')
        self.assertEqual(weblib.Tag.cleanIllegalChar('filler#'), 'filler?')
        self.assertEqual(weblib.Tag.cleanIllegalChar('filler+'), 'filler?')
        self.assertEqual(weblib.Tag.cleanIllegalChar('filler:'), 'filler?')

        xascii = r""" !"$%&'()*-./0123456789;<=>?ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~""" + '\x7f'
        self.assertEqual(weblib.Tag.cleanIllegalChar(xascii), xascii)


class TestWeblib(unittest.TestCase):

    TESTFILE_PATH = testpath/'test_weblib/weblib.dat'

    def setUp(self):
        self.store = store.Store()
        self.TESTTEXT = file(self.TESTFILE_PATH,'rb').read()
        self.store.load('*test*weblib*', StringIO.StringIO(self.TESTTEXT))

    def test_default_tag(self):
        # start from empty wlib
        self.store.load('*test*buffer*', StringIO.StringIO())
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
        wlib = self.store.wlib

        tid = wlib.tags.getByName('English').id
        isCC = lambda: 'c' in wlib.tags.getByName('English').flags

        self.assertTrue(not isCC())

        wlib.setCategoryCollapse(tid, True)
        self.assertTrue(isCC())

        wlib.setCategoryCollapse(tid, False)
        self.assertTrue(not isCC())


    def test_visit(self):
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


    def test_category_setdescription(self):
        wlib = self.store.wlib

        # before
        self.assertEqual(len(wlib.tags), 6)

        # replace Kremlin with Buckingham
        wlib.category.setDescription(u"""
        Buckingham
          Русский
          Français
          日本語
          English
        """  )

        # after
        self.assertEqual(len(wlib.tags), 7)
        self.assertTrue(wlib.tags.getByName('Buckingham'))      # created new tag

        cat_tags = [node.data for node,_ in wlib.category.root.dfs() if node.data]
        for tag in cat_tags:
            self.assertTrue(tag in wlib.tags)                   # these are all real tags

        self.assertEqual([tag.name for tag in cat_tags], [
            u'Buckingham',
            u'Русский',
            u'Français',
            u'日本語',
            u'English',
        ])

        uncat_tags = wlib.category.getUncategorized()
        self.assertEqual([tag.name for tag in uncat_tags], [
            u'inbox',
            u'Kremlin'
        ])


    def test_makeTags(self):
        # before
        wlib = self.store.wlib
        self.assertEqual(len(wlib.tags), 6)

        # makeTags() with ''
        tags = weblib.makeTags(self.store, '')
        self.assert_(not tags)
        self.assertEqual(len(wlib.tags), 6)

        # makeTags() with spaces
        tags = weblib.makeTags(self.store, '    ')
        self.assert_(not tags)
        self.assertEqual(len(wlib.tags), 6)

        # makeTags() with existing tags
        tags = weblib.makeTags(self.store, 'English,Kremlin')
        self.assertEqual(len(tags), 2)
        self.assertEqual(len(wlib.tags), 6)

        # makeTags() with new tags
        tags = weblib.makeTags(self.store, 'T1,T2,T3')
        self.assertEqual(len(tags), 3)
        self.assertEqual(len(wlib.tags), 9)

        # makeTags() with existing and new tags
        tags = weblib.makeTags(self.store, 'T4,T5,English,Kremlin')
        self.assertEqual(len(tags), 4)
        self.assertEqual(len(wlib.tags), 11)


    def test_makeTags_invalid(self):
        self.assertRaises( ValueError,
            weblib.makeTags,
            self.store,
            '@100',
            )


if __name__ == '__main__':
    unittest.main()
