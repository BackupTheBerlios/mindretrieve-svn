# -*- coding: utf-8 -*-
import datetime
import sets
import StringIO
import sys
import unittest

from minds.safe_config import cfg as testcfg
from minds import weblib
from minds.weblib import store
from minds.weblib import query_wlib

testpath = testcfg.getpath('testDoc')


class TestQuery(unittest.TestCase):

    TESTFILE_PATH = testpath/'test_weblib/weblib.dat'

    def setUp(self):
        self.store = store.Store()
        self.TESTTEXT = file(self.TESTFILE_PATH,'rb').read()
        self.store.load('*test*weblib*', StringIO.StringIO(self.TESTTEXT))

        # need because some code get store instance thru store.getStore()
        store.store_instance = self.store


    def test_find_url(self):
        wlib = self.store.wlib
        self.assertEqual(query_wlib.find_url(wlib,''), [])
        result = query_wlib.find_url(wlib,'http://www.mindretrieve.net/')
        result = [item.id for item in result]
        self.assertEqual(result, [1])


    def test_query_tags(self):
        wlib = self.store.wlib
        result = query_wlib.query_tags(wlib, 'inbo', None)
        result = [tag.name for tag in result]
        self.assertEqual(result, ['inbox'])


    def test_query_by_tags(self):
        wlib = self.store.wlib
        ktag =  wlib.tags.getByName('Kremlin')
        positions = query_wlib.query_by_tag(wlib, ktag)

        self.assertEqual(len(positions), 5)     # 5 tags under Kremlin
        self.assertEqual(positions[0].tag.name, u'Kremlin')
        self.assertEqual(positions[1].tag.name, u'Русский')
        self.assertEqual(positions[2].tag.name, u'Français')
        self.assertEqual(positions[3].tag.name, u'日本語')
        self.assertEqual(positions[4].tag.name, u'English')

        self.assertEqual(len(positions[0].items), 0)
        self.assertEqual(len(positions[1].items), 1)
        self.assertEqual(len(positions[2].items), 1)
        self.assertEqual(len(positions[3].items), 1)
        self.assertEqual(len(positions[4].items), 1)


    def test_query(self):
        wlib = self.store.wlib

        # 4 webpages have wiki
        result = query_wlib.query(wlib, 'wiki', None)
        self.assertTrue(result)
        self.assertEqual(len(result), 4)

        # 1 match url
        result = query_wlib.query(wlib, '.net', None)
        self.assertTrue(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0].id, 1)

        # 1 match nickname
        result = query_wlib.query(wlib, '_nickname_', None)
        self.assertTrue(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0].id, 1)


    def test_queryRoot(self):
        wlib = self.store.wlib
        result = query_wlib.queryRoot(wlib)
        self.assertEqual(result, [])    # nothing match no tag


if __name__ == '__main__':
    unittest.main()
