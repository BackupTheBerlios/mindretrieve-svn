"""
"""

import calendar, datetime, time
import StringIO
import sys
import traceback
import unittest

import PyLucene

from minds.safe_config import cfg as testcfg
from minds import messagelog
from minds import qmsg_processor
from minds import distillML
from minds import docarchive
from minds import lucene_logic
from minds.util import fileutil
from minds.util import patterns_tester


testpath = testcfg.getpath('testDoc')


def _makeMeta(uri, date, etag, last_modified):
    """ Utility to build meta """

    ts = qmsg_processor._parseTimestamp(date)   # do a roundtrip to verify the format
    date = qmsg_processor._formatTimestamp(ts)

    meta = {}
    if uri:           meta['uri'          ] = uri
    if date:          meta['date'         ] = date
    if etag:          meta['etag'         ] = etag
    if last_modified: meta['last-modified'] = last_modified
    return meta


def _purge(p):
    if p.exists():
        p.rmtree()


class TestBackgroundTask(unittest.TestCase):
    """ Test qmsg's background index process and misc utilities. """

    def setUp(self):

        messagelog.mlog = messagelog.MsgLogger()

        # prepare some configuration for this test
        self.interval0     = testcfg.get('indexing.interval'    )
        self.numDoc0       = testcfg.get('indexing.numDoc'      )
        self.max_interval0 = testcfg.get('indexing.max_interval')
        testcfg.set('indexing.interval'    , '3'  )
        testcfg.set('indexing.numDoc'      , '5' )
        testcfg.set('indexing.max_interval', '360')

        # make dummy queued msg 0.tmp
        self.logpath = testcfg.getpath('logs')
        self.path0 = self.logpath/'0.tmp'
        self.path0.touch() # create empty file

        dt0 = datetime.datetime(2000,1,1,10,00,0)
        mtime = time.mktime(dt0.timetuple())            # first queued: 2000-1-1 10:00 localtime
        self.path0.utime((mtime, mtime))



    def tearDown(self):
        """ Reset things we have altered. """
        messagelog.mlog = messagelog.MsgLogger()                # reset messagelog.mlog
        testcfg.set('indexing.interval'    , self.interval0    ) # reset configurations
        testcfg.set('indexing.numDoc'      , self.numDoc0      )
        testcfg.set('indexing.max_interval', self.max_interval0)

        self.path0.remove()                             # remove dummy queued msg



    def test_shouldTransform(self):
        oldValue = messagelog.mlog.lastRequest          # need to borrow lastRequest for testing
        try:
            now = datetime.datetime(2000,1,1,0,3,0)
            last = datetime.datetime(2000,1,1,0,0,0)
            messagelog.mlog.lastRequest = last
            self.assert_(not qmsg_processor._shouldTransform(now,3))
            self.assert_(qmsg_processor._shouldTransform(now,2))

        finally:
            messagelog.mlog.lastRequest = oldValue



    def test_shouldIndex0(self):
        """ no msg queued """

        # 2000-1-1 10:30 localtime
        now = datetime.datetime(2000,1,1,10,30,0)

        self.assertEqual(0, qmsg_processor._shouldIndex(now, self.logpath, []))



    def test_shouldIndex01(self):
        """ msg queued(3) < numDoc(5) """

        queued = ['0.tmp'] * 3

        # 2000-1-1 10:30 localtime
        now = datetime.datetime(2000,1,1,10,30,0)
                                                                                    # lastIssued is None
        self.assertEqual(0, qmsg_processor._shouldIndex(now, self.logpath, queued)) # 0 - do not index

        messagelog.mlog.lastIssued = datetime.datetime(2000,1,1,10,29,0)            # 1 min elapsed
        self.assertEqual(0, qmsg_processor._shouldIndex(now, self.logpath, queued)) # 0 - do not index

        messagelog.mlog.lastIssued = datetime.datetime(2000,1,1,10,27,0)            # 3 min elapsed
        self.assertEqual(0, qmsg_processor._shouldIndex(now, self.logpath, queued)) # 0 - do not index

        messagelog.mlog.lastIssued = datetime.datetime(2000,1,1,9,30,0)             # -60 min elapsed
        self.assertEqual(0, qmsg_processor._shouldIndex(now, self.logpath, queued)) # 0 - do not index



    def test_shouldIndex1(self):
        """ msg queued(5) >= numDoc(5) """

        queued = ['0.tmp'] * 5

        # 2000-1-1 10:30 localtime
        now = datetime.datetime(2000,1,1,10,30,0)
                                                                                    # lastIssued is None
        self.assertEqual(1, qmsg_processor._shouldIndex(now, self.logpath, queued)) # 1 - numDoc has met

        messagelog.mlog.lastIssued = datetime.datetime(2000,1,1,10,29,0)            # 1 min elapsed
        self.assertEqual(0, qmsg_processor._shouldIndex(now, self.logpath, queued)) # 0 - do not index

        messagelog.mlog.lastIssued = datetime.datetime(2000,1,1,10,27,0)            # 3 min elapsed
        self.assertEqual(1, qmsg_processor._shouldIndex(now, self.logpath, queued)) # 1 - numDoc has met

        messagelog.mlog.lastIssued = datetime.datetime(2000,1,1,10,31,0)            # -1 min elapsed (new activity)
        self.assertEqual(0, qmsg_processor._shouldIndex(now, self.logpath, queued)) # 0 - do not index

        messagelog.mlog.lastIssued = datetime.datetime(2000,1,1,11,30,0)            # -60 min elapsed
        self.assertEqual(-1, qmsg_processor._shouldIndex(now, self.logpath, queued))# -1 - fail to evaluate time elapsed
        # see source code for the logic of this decision



    def test_shouldIndex2(self):
        """ Check if time elapsed since first msg (10:00) v.s. max_interval """

        queued = ['0.tmp'] * 3

        # 2000-1-1 10:30 localtime
        now = datetime.datetime(2000,1,1,10,30,0)
                                                                                    # 30 min elapsed
        self.assertEqual(0, qmsg_processor._shouldIndex(now, self.logpath, queued)) # 0 - do not index

        now = datetime.datetime(2000,1,1,16,0,0)                                    # 360 min elapsed
        self.assertEqual(2, qmsg_processor._shouldIndex(now, self.logpath, queued)) # 2 - max_interval has reached

        now = datetime.datetime(2000,1,1,9,0,0)                                     # -60 min elapsed
        self.assertEqual(-2, qmsg_processor._shouldIndex(now, self.logpath, queued))# -2 = fail to evaluete time elapsed



    def test_parseTimestamp(self):

        ts1 = '1990-12-01T12:34:56Z'
        ts2 = '2010-01-31T01:02:03Z'

        dt1 = qmsg_processor._parseTimestamp(ts1)
        dt2 = qmsg_processor._parseTimestamp(ts2)

        self.assertEqual( datetime.datetime(1990,12,1,12,34,56), dt1)
        self.assertEqual( datetime.datetime(2010,1,31,01,02,03), dt2)

        self.assertEqual(ts1, qmsg_processor._formatTimestamp(dt1))
        self.assertEqual(ts2, qmsg_processor._formatTimestamp(dt2))

        self.assertRaises(ValueError, qmsg_processor._parseTimestamp, '')
        self.assertRaises(Exception,  qmsg_processor._parseTimestamp, 1)
        self.assertRaises(ValueError, qmsg_processor._parseTimestamp, 'abcdefghijklmno')



class TestMeta(unittest.TestCase):
    """ Test meta data manipulation during transformation. Also use distillML.writeHeader """

    def setUp(self):
        # set maxuri for testing of meta
        self.maxuri0 = qmsg_processor.g_maxuri
        qmsg_processor.g_maxuri = 30


    def tearDown(self):
        qmsg_processor.g_maxuri = self.maxuri0


    def testMeta0(self):
        """ with minimal meta data """

        minfo = messagelog.MessageInfo._makeTestMinfo([],789,req_path='http://host/path')
        meta = qmsg_processor._extract_meta(minfo, '2004')

        buf = StringIO.StringIO()
        distillML.writeHeader(buf, meta)
        s = buf.getvalue()

        self.assert_(0 <= s.find('uri: http://host/path'))
        self.assert_(0 <= s.find('etag: W/789'          ))
        self.assert_(0 >  s.find('title'                ))
        self.assert_(0 >  s.find('description'          ))
        self.assert_(0 >  s.find('keywords'             ))
        self.assert_(0 >  s.find('last-modified'        ))


    def testMeta1(self):
        """ Full meta data with both etag and last-modified """

        minfo = messagelog.MessageInfo._makeTestMinfo([
                ('Last-Modified', 'Sun, 24 Oct 2004 07:29:44 GMT'),
                ('ETag', '"9b2e763b9bb9c41:8b7"'),
                ('Content-Type', 'text/plain'),],
                789, req_path='http://host/path')
        meta = qmsg_processor._extract_meta(minfo, '2004')

        self.assertEqual(meta['content-type'], 'text/plain')

        meta['title']       = 'val1'    # these usually filled by distillML
        meta['description'] = 'val2'
        meta['keywords']    = 'val3'

        buf = StringIO.StringIO()
        distillML.writeHeader(buf, meta)
        s = buf.getvalue()

        self.assert_(0 <= s.find('uri: http://host/path'))
        self.assert_(0 <= s.find('title: val1'))
        self.assert_(0 <= s.find('description: val2'))
        self.assert_(0 <= s.find('keywords: val3'))
        self.assert_(0 <= s.find('etag: "9b2e763b9bb9c41:8b7"'))
        self.assert_(0 >  s.find('last-modified'))


    def testMeta2(self):
        """ with only Last-Modified """

        minfo = messagelog.MessageInfo._makeTestMinfo([
            ('Last-Modified', 'Sun, 24 Oct 2004 07:29:44 GMT'),],
            789, req_path='http://host/path',)
        meta = qmsg_processor._extract_meta(minfo, '2004')

        buf = StringIO.StringIO()
        distillML.writeHeader(buf, meta)
        s = buf.getvalue()

        self.assert_(0 <= s.find('uri: http://host/path'))
        self.assert_(0 <= s.find('last-modified: Sun, 24 Oct 2004 07:29:44 GMT'))
        self.assert_(0 >  s.find('etag'))


    def testMaxuri(self):
        uri = 'http://host' + '/1234567890'*10
        minfo = messagelog.MessageInfo._makeTestMinfo([], 789, req_path=uri)
        meta = qmsg_processor._extract_meta(minfo, '2004')

        # uri truncated after 30 characters
        self.assertEqual(len(meta['uri']), 30+3)
        self.assertEqual(meta['uri'], 'http://host/1234567890/1234567...')



class TestSearchForArchived(unittest.TestCase):
    """ Test the _searchForArchived() logic """

    def setUp(self):

        # configuration used in this test
        self.archive_interval0 = qmsg_processor.g_archive_interval
        qmsg_processor.g_archive_interval = 0.5

        # setup test index
        m1 = _makeMeta('u1', '1999-01-01T10:00:00Z', 'v0'  , None)
        m2 = _makeMeta('u1', '2000-01-01T10:00:00Z', 'v1'  , None)
        m3 = _makeMeta('u2', '2000-01-01T10:00:00Z', '2000', None)  # note: the '2000' is last-modified
                                                                    # writer.addDocument() expects etag & last-modified
                                                                    # merged already
        writer = lucene_logic.Writer()
        writer.addDocument('1', m1, 'dummy content')
        writer.addDocument('2', m2, 'dummy content')
        writer.addDocument('3', m3, 'dummy content')
        writer.close()

        self.indexer = qmsg_processor.IndexProcess()
        self.indexer.searcher = lucene_logic.Searcher(directory=writer.directory)       ### HACK HACK


    def tearDown(self):
        self.indexer._finish()
        qmsg_processor.g_archive_interval = self.archive_interval0


    def test_not_found(self):
        uri = 'u3'
        meta = _makeMeta(uri, '2000-01-01T10:00:00Z', 'v1', 1999)
        result = self.indexer._searchForArchived(uri, meta)
        self.assertEqual(None, result)


    def test_etag_not_match(self):
        uri = 'u1'
        meta = _makeMeta(uri, '2001-01-01T10:00:00Z', 'v2', None)
        result = self.indexer._searchForArchived(uri, meta)
        self.assertEqual(False, result)


    def test_etag_match(self):
        uri = 'u1'
        meta = _makeMeta(uri, '2001-01-01T10:00:00Z', 'v1', None)
        result = self.indexer._searchForArchived(uri, meta)
        self.assert_(result)
        self.assert_(result.find('v1') >= 0)


    def test_last_modified_not_match(self):
        uri = 'u2'
        meta = _makeMeta(uri, '2001-01-01T10:00:00Z', None, '2001')
        result = self.indexer._searchForArchived(uri, meta)
        self.assertEqual(False, result)


    def test_last_modified_match(self):
        uri = 'u2'
        meta = _makeMeta(uri, '2001-01-01T10:00:00Z', None, '2000')
        result = self.indexer._searchForArchived(uri, meta)
        self.assert_(result)
        self.assert_(result.find('2000') >= 0)


    def test_etag_match_previous(self):
        # In this unusual case the etag match the second latest but not the latest.
        # Our algorithm would return a no match.
        uri = 'u1'
        meta = _makeMeta(uri, '2001-01-01T10:00:00Z', 'v0', None)
        result = self.indexer._searchForArchived(uri, meta)
        self.assertEqual(False, result)


    def test_within_archive_interval(self):
        uri = 'u1'
        meta = _makeMeta(uri, '2000-01-01T11:00:00Z', 'v2', None)   # only 1 hour after last archived
        result = self.indexer._searchForArchived(uri, meta)
        self.assert_(result)
        self.assert_(result.find('2000-01-01T10:00:00Z') >= 0)


    def test_after_archive_interval(self):
        uri = 'u1'
        meta = _makeMeta(uri, '2000-01-01T22:00:01Z', 'v2', None)   # > 12 hour after last archived
        result = self.indexer._searchForArchived(uri, meta)
        self.assertEqual(False, result)



class TestQmsg(unittest.TestCase):
    """ Test the main transformation process """

    def setUp(self):

        self.indexpath = testcfg.getpath('archiveindex')
        self.assertEqual(
            self.indexpath,'testdata/archive/index')    # check to prevent deleting things in wrong dir due to config goof
        _purge(self.indexpath)                          # start with empty index

        self.arcdocpath = testcfg.getpath('archive')
        self.assertEqual(self.arcdocpath,'testdata/archive')
        try:
            self.arcdocpath.makedirs()
        except OSError, e:
            # ignore OSError: [Errno 17] File exists
            if e.errno != 17:
                raise

        self.logpath = testcfg.getpath('logs')
        self.assertEqual(self.logpath,'testlogs')

        id = docarchive.idCounter.getNewId()
        self.assert_(int(id) < 999000, id)              # don't expect this to happen for test data; just double check.

        docarchive.idCounter._endId = 999000            # prepared docarc to start output from id #999000

        self._cleanup()



    def _cleanup(self):
        # remove *.qlog and *.qtxt
        files = fileutil.listdir(self.logpath, qmsg_processor.QLOG_PATTERN) + \
                fileutil.listdir(self.logpath, qmsg_processor.QTXT_PATTERN)
        for f in files:
            try: (self.logpath/f).remove()
            except OSError: traceback.print_exc()



    def tearDown(self):
        arcpath = self.arcdocpath/'000999.zip'
        if arcpath.exists():
            arcpath.remove()
        docarchive.idCounter = docarchive.IdCounter()   # reinstantiate to reset its id range

        # remove archive and index
        _purge(self.arcdocpath)



    def _fetch_qlogs(self, files):
        """ copy files to the log directory and assign an id to them """
        queued = []
        for i, src in enumerate(files):
            dest = '%09d.qlog' % (i+1)
            queued.append(dest)
            (testpath/src).copy(self.logpath/dest)

        return queued



    def _check_archive_doc(self, docid, *signatures):
        fp = docarchive.get_document(docid)             # test docid exists (i.e. no exception)
        data = fp.read(1024)
        for s in signatures:
            self.assert_(0 <= data.find(s), s)          # have signatures



    def testTransformDocs(self):

        TEST_FILES = [
            '200(getopt_org).mlog',         # 1
            'gif.qlog',                     # 2 - weed
            'empty_response.mlog',          # 3 - bad
            'gzipped(slashdot).mlog',       # 4
            'favicon.ico_text(nutch).mlog', # 5 - weed txt
            'plaintext.mlog',               # 6
        ]
        queued = self._fetch_qlogs(TEST_FILES)

        for src in queued:                                          # controlled test: .qlog files are copied
            qlogpath = self.logpath/src
            self.assert_(qlogpath.exists(), qlogpath)

        dt0 = datetime.datetime(2000,1,1,12,34,56)                  # mtime 2000-1-1 12:34:56 GMT
        mtime = calendar.timegm(dt0.utctimetuple())                 # tricky to convert to time.gmtime()?!
        lastpath = self.logpath/queued[-1]
        lastpath.utime((mtime, mtime))

        invalid_entries = ['non_exist', '']                         # throw a monkey wrench into the process!

        # -------------------------------------
        # This is the main process to be tested
        # -------------------------------------
        transformed, discarded = qmsg_processor.TransformProcess().run(self.logpath, invalid_entries + queued)

        self.assertEqual(3, transformed)
        self.assertEqual(4, discarded)                              # 3 bad + 1 invalid + 1 empty

        for src in queued:                                          # test all .qlog files are being removed
            srcpath = self.logpath/src
            self.assert_(not srcpath.exists(), srcpath)

        qtxts = ['000000001', '000000004', '000000006']             # test .qtxt created
        for qtxt in qtxts:
            qtxtpath = self.logpath/(qtxt + '.qtxt')
            self.assert_(qtxtpath.exists(), qtxtpath)



    def test_discarded_archived(self):

        # add a doc to index that matches creative_commons.qlog's etag
        writer = lucene_logic.Writer(self.indexpath)
        writer.addDocument('1',
            _makeMeta('http://www.getopt.org/luke/', '2000-01-01T10:00:00Z', '"d00b7-2491-40d75aea"', None),
            'dummy content')
        writer.close()

        queued = self._fetch_qlogs(['200(getopt_org).mlog', 'gzipped(slashdot).mlog', 'gzipped(slashdot).mlog'])
        transformed, discarded = qmsg_processor.TransformProcess().run(self.logpath, queued)
        self.assertEqual(3, transformed)
        self.assertEqual(0, discarded)

        queued = [
            '000000001.qtxt',                                       # archived(v="d00b7-2491-40d75aea")
            '000000002.qtxt',
            '000000003.qtxt',                                       # archived(v=W/13865) found in freshdocs
        ]
        indexed, discarded = qmsg_processor.IndexProcess().run(self.logpath, queued)
        self.assertEqual(1, indexed)
        self.assertEqual(2, discarded)

        self.assertEqual(999001, int(docarchive.idCounter.getNewId())) # test 1 archive id being used



    def test_indexDocs(self):

        files = ['000000001.qtxt', '000000004.qtxt', '000000006.qtxt']
        for f in files:
            (testpath/f).copy(self.logpath/f)

        invalid_entries = ['non_exist', '']                         # throw a monkey wrench into the process!

        # -------------------------------------
        # This is the main process to be tested
        # -------------------------------------
        numIndexed, numDiscarded = qmsg_processor.IndexProcess().run(self.logpath, invalid_entries + files)

        self.assertEqual(3, numIndexed)

        self.assertEqual(999003, int(docarchive.idCounter.getNewId())) # test only 3 archive id being used

        searcher = lucene_logic.Searcher(pathname=self.indexpath)

        # todo: put the search logic into lucene_logic?

        # search for documents indexed and verify their meta data
        query = PyLucene.QueryParser.parse('slashdot', 'content', PyLucene.StandardAnalyzer())
        hits = searcher.searcher.search(query)
        self.assert_(hits.length > 0)
        doc = hits.doc(0)
        self.assertEqual(doc.get('uri'), 'http://slashdot.org/')
        self.assertEqual(doc.get('etag'), 'W/13865')
        self.assertEqual(len(doc.get('date')), 20)

        query = PyLucene.QueryParser.parse('Lucene Index Toolbox', 'content', PyLucene.StandardAnalyzer())
        hits = searcher.searcher.search(query)
        self.assert_(hits.length > 0)
        doc = hits.doc(0)
        self.assertEqual(doc.get('uri'), 'http://www.getopt.org/luke/')
        self.assertEqual(doc.get('etag'), '"d00b7-2491-40d75aea"')
        self.assertEqual(len(doc.get('date')), 20)

        query = PyLucene.QueryParser.parse('Copyright', 'content', PyLucene.StandardAnalyzer())
        hits = searcher.searcher.search(query)
        self.assert_(hits.length > 0)
        doc = hits.doc(0)
        self.assertEqual(doc.get('uri'), 'http://local.tungwaiyip.info/test/plaintext.txt')
        self.assertEqual(doc.get('date'), '2000-01-01T12:34:56Z')

        searcher.close()

        # test docs are store in archive
        self._check_archive_doc('000999000', 'Luke - Lucene Index Toolbox', 'uri: http://www.getopt.org/luke/')
        self._check_archive_doc('000999001', 'Slashdot: News for nerds, stuff that matters')
        self._check_archive_doc('000999002', 'All rights reserved.', 'date: 2000-01-01T12:34:56Z')


    def test_backgroundIndexTask(self):

        TEST_FILES = [
            '200(getopt_org).mlog',         # 1
            'gif.qlog',                     # 2 - weed
            'empty_response.mlog',          # 3 - bad
            'gzipped(slashdot).mlog',       # 4
            'favicon.ico_text(nutch).mlog', # 5 - weed txt
            'plaintext.mlog',               # 6
        ]
        queued = self._fetch_qlogs(TEST_FILES)

        transformed, indexed, discarded = qmsg_processor.backgroundIndexTask(True)
        self.assertEqual((transformed, indexed, discarded), (3,3,3))

        self._check_archive_doc('000999000', 'Luke - Lucene Index Toolbox', 'uri: http://www.getopt.org/luke/')
        self._check_archive_doc('000999001', 'Slashdot: News for nerds, stuff that matters')
        self._check_archive_doc('000999002', 'All rights reserved.')



    def test_backgroundIndexTask1(self):

        # break the process into two batches

        TEST_FILES = [
            '200(getopt_org).mlog',         # 1
            'gif.qlog',                     # 2 - weed
            'empty_response.mlog',          # 3 - bad
        ]
        queued = self._fetch_qlogs(TEST_FILES)

        transformed, indexed, discarded = qmsg_processor.backgroundIndexTask(True)
        self.assertEqual((transformed, indexed, discarded), (1,1,2))

        self._check_archive_doc('000999000', 'Luke - Lucene Index Toolbox', 'uri: http://www.getopt.org/luke/')

        # second batch
        TEST_FILES = [
            'gzipped(slashdot).mlog',       # 4
            'favicon.ico_text(nutch).mlog', # 5 - weed txt
            'plaintext.mlog',               # 6
        ]
        queued = self._fetch_qlogs(TEST_FILES)

        transformed, indexed, discarded = qmsg_processor.backgroundIndexTask(True)
        self.assertEqual((transformed, indexed, discarded), (2,2,1))

        self._check_archive_doc('000999000', 'Luke - Lucene Index Toolbox', 'uri: http://www.getopt.org/luke/')
        self._check_archive_doc('000999001', 'Slashdot: News for nerds, stuff that matters')
        self._check_archive_doc('000999002', 'All rights reserved.')



    def test_backgroundIndexTask2(self):

        # break the process into two batches, simulate restart engine

        TEST_FILES = [
            '200(getopt_org).mlog',         # 1
            'gif.qlog',                     # 2 - weed
            'empty_response.mlog',          # 3 - bad
        ]
        queued = self._fetch_qlogs(TEST_FILES)

        transformed, indexed, discarded = qmsg_processor.backgroundIndexTask(True)
        self.assertEqual((transformed, indexed, discarded), (1,1,2))

        self._check_archive_doc('000999000', 'Luke - Lucene Index Toolbox', 'uri: http://www.getopt.org/luke/')

        # simulate restarting engine by reinstantiate idCounter
        docarchive.idCounter = docarchive.IdCounter()

        # second batch
        TEST_FILES = [
            'gzipped(slashdot).mlog',       # 4
            'favicon.ico_text(nutch).mlog', # 5 - weed txt
            'plaintext.mlog',               # 6
        ]
        queued = self._fetch_qlogs(TEST_FILES)

        transformed, indexed, discarded = qmsg_processor.backgroundIndexTask(True)
        self.assertEqual((transformed, indexed, discarded), (2,2,1))

        self._check_archive_doc('000999000', 'Luke - Lucene Index Toolbox', 'uri: http://www.getopt.org/luke/')
        self._check_archive_doc('000999001', 'Slashdot: News for nerds, stuff that matters')
        self._check_archive_doc('000999002', 'All rights reserved.')


if __name__ == '__main__':
    unittest.main()
