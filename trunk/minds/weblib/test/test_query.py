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
        result = query_wlib.query_by_tag(wlib, ktag)
        self.assertTrue(result)
        self.assertEqual(len(result.children), 4)   # 4 tags under Kremlin
        # TODO: clarify query_by_tag's result

    def test_query(self):
        wlib = self.store.wlib
        result = query_wlib.query(wlib, 'wiki', None)
        self.assertTrue(result)
        self.assertEqual(len(result), 4)   # 4 webpages have wiki
        result = query_wlib.query(wlib, '.net', None)
        self.assertTrue(result)
        self.assertEqual(len(result), 1)   # 1 match url


    def test_queryRoot(self):
        wlib = self.store.wlib
        result = query_wlib.queryRoot(wlib)
        self.assertEqual(result, [])    # nothing match no tag


if __name__ == '__main__':
    unittest.main()
