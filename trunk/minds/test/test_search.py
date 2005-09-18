"""
"""

import sys
import StringIO
import unittest

from minds.safe_config import cfg as testcfg
from minds import docarchive
from minds import lucene_logic
from minds import search


def _makeMeta(uri, date, etag, last_modified):
    """ Utility to build meta """
    meta = {}
    if uri:           meta['uri'          ] = uri
    if date:          meta['date'         ] = date
    if etag:          meta['etag'         ] = etag
    if last_modified: meta['last-modified'] = last_modified
    return meta


def _add_documents(data):
    """ Helper to add documents.
        data is list of (id, content)
    """
    header = "uri: dummy\r\n\r\n"
    ah = docarchive.ArchiveHandler('w')
    try:
        for id, content in data:
            ah.add_document(id, StringIO.StringIO(header+content))
    finally:
        ah.close()



class TestSearch(unittest.TestCase):

    def setUp(self):
        self.indexpath = testcfg.getpath('archiveindex')
        self.apath = testcfg.getpath('archive')
        self._cleanup()
        self.populateTestDocs()


    def _cleanup(self):
        assert(self.apath == 'testdata/archive')    # avoid deleting wrong data in config goof
        self.apath.rmtree()


    def populateTestDocs(self):

        testdocs = [
            ('000000001', 'dummy content1'),
            ('000000002', 'content2'),
            ('000000003', 'dummy content3'),
        ]
        _add_documents(testdocs)

        writer = lucene_logic.Writer(pathname=self.indexpath)
        writer.addDocument(testdocs[0][0], _makeMeta('u1', '1999-01-01T10:00:00Z', 'v0'  , None), testdocs[0][1])
        writer.addDocument(testdocs[1][0], _makeMeta('u2', '2000-01-01T10:00:00Z', 'v1'  , None), testdocs[1][1])
        writer.addDocument(testdocs[2][0], _makeMeta('u3', '2000-01-01T10:00:00Z', '2000', None), testdocs[2][1])
        writer.close()


    def tearDown(self):
        self._cleanup()


    def testSearch(self):

        query = search.parseQuery('dummy')
        length, result = search.search(query, 0, 10)
        self.assertEqual(2, length)

        # item 1 and 3 expect to match, with item 3 come first (reverse insertion {chronological} order)
        # verify highlighted match
        item = result[0]
        self.assertEqual('000000003', item.docid)
        self.assertEqual('u3', item.uri)
        self.assert_(item.description.find("<span class='highlight'>dummy</span>") >= 0)

        item = result[1]
        self.assertEqual('000000001', item.docid)
        self.assertEqual('u1', item.uri)
        self.assert_(item.description.find("<span class='highlight'>dummy</span>") >= 0)

        #for r in result: print r.description, r.score, r.docid


if __name__ == '__main__':
    unittest.main()