"""
"""

import os, os.path, sys
import shutil
import unittest

from config_help import cfg
from minds import lucene_logic



class TestLuceneLogic(unittest.TestCase):

    def setUp(self):
        self.dbindex = cfg.getPath('archiveindex')
        self.cleanup()


    def tearDown(self):
        self.cleanup()


    def cleanup(self):
        self.assertEqual('testdata/archive/index', self.dbindex)      # don't delete wrong data
        if os.path.exists(self.dbindex):
            shutil.rmtree(self.dbindex)


    def _test_index_and_search(self, **args):

        writer = lucene_logic.Writer(**args)
        try:
            if len(args) == 0:                              # special case for RAM directory
                args = { 'directory': writer.directory }    # pass the RAM directory for subsequence searching

            if writer.docCount() <= 1:
                writer.addDocument(u'1', {'uri': u'http://a', 'date': '2004'}, u'content1')
                writer.addDocument(u'2', {'uri': u'http://a', 'date': '2005'}, u'content2')
        finally:
            writer.close()

        reader = lucene_logic.Reader(**args)
        try:
            self.assertEqual(reader.numDocs(), 3)           # 2 document added + 1 version document
            self.assert_(reader.hasDocument(u'1'))
            self.assert_(not reader.hasDocument(u'3'))
        finally:
            reader.close()

        searcher = lucene_logic.Searcher(**args)
        try:
            hits = searcher.searchLast(u'http://a')
            self.assertEqual(len(hits), 2)
            self.assertEqual(hits.doc(0).get('docid'), u'2')
            self.assertEqual(hits.doc(0).get('date'), u'2005')
            self.assertEqual(hits.doc(1).get('docid'), u'1')
            self.assertEqual(hits.doc(1).get('date'), u'2004')

            hits = searcher.searchLast(u'not exist')
            self.assertEqual(len(hits), 0)
        finally:
            searcher.close()


    def test_RAM(self):
        self.assert_(not os.path.exists(self.dbindex))
        self._test_index_and_search()
        self.assert_(not os.path.exists(self.dbindex))


    def test_FSDirectory(self):
        # iteration 1: start with empty diretory
        self.assert_(not os.path.exists(self.dbindex))
        self._test_index_and_search(pathname=self.dbindex)

        # iteration 2: with existing index
        self.assert_(os.path.exists(self.dbindex))
        self._test_index_and_search(pathname=self.dbindex)


    def test_version(self):
        # check for the version document added to new index
        reader = lucene_logic.Reader()
        version = cfg.get('version', 'number', '?')
        self.assertEqual(1, reader.numDocs())
        self.assertEqual(version, reader.getVersion())


if __name__ == '__main__':
    unittest.main()