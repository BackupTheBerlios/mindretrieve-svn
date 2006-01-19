"""Assist to log messages as it pass through the proxy.
Note that there can be simultaneous connections.
Also assit the background archiver to process the messages logged.
"""

import datetime
import StringIO
import time
import unittest

from minds.safe_config import cfg as testcfg
from minds import cachefile
from minds import messagelog
from minds.util import multiblockfile


class TestMessageInfo(unittest.TestCase):

    TESTFILE_PATH = testcfg.getpath('testDoc')/'creative_commons.qlog'
    req_path  = 'http://creativecommons.org/'
    host_only = 'creativecommons.org'


    def setUp(self):
        self.fp = None


    def tearDown(self):
        if self.fp: self.fp.close()


    def testParseMessageLog00(self):
        fp = StringIO.StringIO('')
        self.assertRaises(IOError, messagelog.MessageInfo.parseMessageLog, fp)


    def testParseMessageLog01(self):
        fp = StringIO.StringIO('')
        multiblockfile.MbWriter(fp).close()             # make one 0 len block
        fp.seek(0)
        self.assertRaises(messagelog.ParseMessageLogError, messagelog.MessageInfo.parseMessageLog, fp)


    def testParseMessageLog(self):
        self.fp = file(self.TESTFILE_PATH,'rb')
        m = messagelog.MessageInfo.parseMessageLog(self.fp)

        self.assertEqual(m.id               , None          )
        self.assertEqual(m.discard          , False         )

        self.assertEqual(m.command          , 'GET'         )
        self.assertEqual(m.req_path         , self.req_path )
        self.assertEqual(m.host             , self.host_only)
        self.assertEqual(m.host_noport      , self.host_only)

# req_headers wasn't initialized by parseMessageLog()
#
#        self.assertEqual(len(m.req_headers) , 8             )

        self.assertEqual(m.status           , 200           )
        self.assertEqual(len(m.rsp_headers) , 7             )
        self.assertEqual(m.clen             , 12158         )
        self.assertEqual(m.ctype            , 'html'        )
        self.assertEqual(m.flags            , '___'         )

        self.assertEqual(m.rsp_headers['last-modified'], 'Sat, 15 Jan 2005 18:21:41 GMT')


    def testTruncated(self):

        # OK, content-length not specified
        minfo = messagelog.MessageInfo._makeTestMinfo([('content-type','text/plain')],7)
        self.assert_(not minfo.discard)
        self.assertEqual(7, minfo.clen)
        self.assertEqual('___', minfo.flags)

        # OK, content-length invalid
        minfo = messagelog.MessageInfo._makeTestMinfo([('content-length','?'),('content-type','text/plain')],7)
        self.assert_(not minfo.discard)
        self.assertEqual(7, minfo.clen)
        self.assertEqual('___', minfo.flags)

        # OK, content-length match bytes received
        minfo = messagelog.MessageInfo._makeTestMinfo([('content-length','7'),('content-type','text/plain')],7)
        self.assert_(not minfo.discard)
        self.assertEqual(7, minfo.clen)
        self.assertEqual('___', minfo.flags)

        # truncated, content-length not match bytes received
        minfo = messagelog.MessageInfo._makeTestMinfo([('content-length','100'),('content-type','text/plain')],7)
        self.assert_(minfo.discard)
        self.assertEqual(100, minfo.clen)
        self.assertEqual('__T', minfo.flags)


    def testDiscardFilter(self):
        make = messagelog.MessageInfo._makeTestMinfo
        headers = [('content-type','text/plain')]
        path = 'http://abc.com/'

        # baseline case
        minfo = make(headers, 7, method='GET', req_path=path, status='200')
        self.assert_(not minfo.discard)
        self.assertEqual('___', minfo.flags)

        # method is not GET
        minfo = make(headers, 7, method='POST', req_path=path, status='200')
        self.assert_(minfo.discard)
        self.assertEqual('___', minfo.flags)

        # status is not 200
        minfo = make(headers, 7, method='GET', req_path=path, status='304')
        self.assert_(minfo.discard)
        self.assertEqual('___', minfo.flags)

        # not text or html
        minfo = make([('content-type','text/xml')], 7, method='GET', req_path=path, status='200')
        self.assert_(minfo.discard)
        self.assertEqual('___', minfo.flags)

        # Authorization
        minfo = make(headers, 7, method='GET', req_path=path, req_headers=[('Authorization','Basic abcde')], status='200')
        self.assert_(minfo.discard)
        self.assertEqual('__A', minfo.flags)

        # no-store
        minfo = make(headers+[('Cache-Control','no-store')], 7, method='GET', req_path=path, status='200')
        self.assert_(minfo.discard)
        self.assertEqual('S__', minfo.flags)

        # no-store variation
        minfo = make(headers+[('Cache-Control','max-age=0, no-store ')], 7, method='GET', req_path=path, status='200')
        self.assert_(minfo.discard)
        self.assertEqual('S__', minfo.flags)

        # truncated
        minfo = make(headers+[('Content-Length','100')], 7, method='GET', req_path=path, status='200')
        self.assert_(minfo.discard)
        self.assertEqual('__T', minfo.flags)

        # localhost
        minfo = make(headers, 7, method='GET', req_path='http://localhost:8080/', status='200')
        self.assert_(minfo.discard)
        self.assertEqual('___', minfo.flags)



class MockCacheFile(cachefile.CacheFile):
    """ Only record the filenames in self.saved instead of writing to disk """

    def __init__(self, *args):
        super(MockCacheFile,self).__init__(*args)
        self.saved = []

    def _save(self, filename):
        self.saved.append(filename)

    def discard(self):
        self.saved = None



class MsgLoggerFixture(messagelog.MsgLogger):
    """ overrides _listdir() to help test _findHighestId """

    def __init__(self, *args):
        super(MsgLoggerFixture,self).__init__(*args)
        self.dirlist = []

    def _listdir(self, logdir):
        return self.dirlist



class TestMsgLogger(unittest.TestCase):

    def setUp(self):
        self.mlog = MsgLoggerFixture()
        self.minfo = messagelog.MessageInfo._makeTestMinfo([('content-type','text/plain')],7)
        self.minfoX = messagelog.MessageInfo._makeTestMinfo([('content-type','text/plain')],7,status='404')
        self.assert_(not self.minfo.discard)    # good minfo
        self.assert_(self.minfoX.discard)       # discard minfo
        self.starttime = datetime.datetime.now()


    def test_findHighestId(self):

        # no file
        self.mlog.dirlist = []
        self.assertEqual(self.mlog._findHighestId(), 0)

        # irrevelant file
        self.mlog.dirlist = ['abc']
        self.assertEqual(self.mlog._findHighestId(), 0)

        # 1 files
        self.mlog.dirlist = ['000000001.qlog']
        self.assertEqual(self.mlog._findHighestId(), 1)

        # 2 files
        self.mlog.dirlist = ['000000001.qlog', '000000007.qlog']
        self.assertEqual(self.mlog._findHighestId(), 7)

        # more files
        self.mlog.dirlist = ['000000001.qlog', '000000007.qlog', 'def', '000000009.qlog']
        self.assertEqual(self.mlog._findHighestId(), 9)


    def testLastIssued(self):

        self.assertEqual(self.mlog.lastIssued, None)

        id = self.mlog.getId()
        d0 = self.mlog.lastIssued
        self.assertNotEqual(d0, None)

        time.sleep(0.3)

        id = self.mlog.getId()
        d1 = self.mlog.lastIssued
        self.assertNotEqual(d1, None)
        self.assert_(d1 > d0)


    def _invoke_dispose(self, minfo, cfp, mlog):
        """ Helper to set 'mlog' config and then invoke dispose() """

        mlog0 = testcfg.get('messagelog.mlog')
        testcfg.cparser.set('messagelog', 'mlog', mlog)
        try:
            self.mlog.dispose(minfo, cfp, self.starttime)
        finally:
            testcfg.set('messagelog.mlog', mlog0)


    def testDispose_00(self):
        # no mlog, discarded
        self.mlog.currentId = 1
        cfp = MockCacheFile(10)
        self._invoke_dispose(self.minfoX, cfp, '0')
        self.assertEqual(cfp.saved, [])
        self.assertEqual(self.mlog.currentId, 1)


    def testDispose_01(self):
        # no mlog, not discarded
        self.mlog.currentId = 1
        cfp = MockCacheFile(10)
        self._invoke_dispose(self.minfo, cfp, '0')
        self.assertEqual(cfp.saved, ['000000001.qlog'])
        self.assertEqual(self.mlog.currentId, 2)


    def testDispose_10(self):
        # mlog, discarded
        self.mlog.currentId = 1
        cfp = MockCacheFile(10)
        self._invoke_dispose(self.minfoX, cfp, '1')
        self.assertEqual(cfp.saved, ['000000001.mlog'])
        self.assertEqual(self.mlog.currentId, 2)


    def testDispose_11(self):
        # mlog, not discarded
        self.mlog.currentId = 1
        cfp = MockCacheFile(10)
        self._invoke_dispose(self.minfo, cfp, '1')
        self.assertEqual(cfp.saved, ['000000001.qlog', '000000001.mlog'])
        self.assertEqual(self.mlog.currentId, 2)



if __name__ == '__main__':
    unittest.main()