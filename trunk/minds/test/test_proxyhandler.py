"""
"""

import os.path
import traceback
import unittest

from minds.safe_config import cfg as testcfg
from minds import messagelog
from minds import proxyhandler
from minds.util import fileutil
from minds.util.multiblockfile import MbReader

testpath = testcfg.getpath('testDoc')
logpath = testcfg.getpath('logs')

class TestProxyHandler(unittest.TestCase):

    # note that we uses proxyhandler.testHandleMlog() to run through most
    # of ProxyHandler. However network element like select is not exercised.

    def setUp(self):
        self.assertEqual(logpath, 'testlogs')
        self.cleanup()


    def cleanup(self):
        # remove existing log files
        # hardcode the 'testlogs' directory. Avoid config goof and deleting real data.
        files = fileutil.listdir(logpath, messagelog.mlog.log_pattern)
        for f in files:
            try: (logpath/f).remove()
            except OSError: traceback.print_exc()
        messagelog.mlog = messagelog.MsgLogger()    # reset currentId after cleanup()


    def tearDown(self):
        self.cleanup()


    def testRequestForwarded(self):
        pHandler = proxyhandler.testHandleMlog(testpath/'creative_commons.qlog')

        # check connect to destination directly
        self.assertEqual(pHandler.connect_dest, 'creativecommons.org')

        # check correct request message
        pHandler.s_out.seek(0)
        s_out = pHandler.s_out.read()
        self.assert_(s_out.find('GET / HTTP/1.0\r\n') == 0)
        self.assert_(s_out.find('Host: creativecommons.org') > 0)
        self.assert_(s_out.find('Connection: close') > 0)
        self.assert_(s_out.find('Proxy-connection: close') < 0)

        # check 1 message logged
        self.assertEqual(messagelog.mlog.currentId, 2)

        # the new logged file should be identical to the orignal
        logpath = messagelog.mlog._getMsgLogPath('000000001')
        self.assert_(os.path.exists(logpath))
        self.assertEqual(file(logpath,'rb').read(), (testpath/'creative_commons.qlog').open('rb').read())


    def testNextProxy(self):
        testServer = proxyhandler.TestServer(next_proxy='myproxy:8080')
        pHandler = proxyhandler.testHandleMlog(testpath/'creative_commons.qlog', server=testServer)

        # check connect to destination directly
        self.assertEqual(pHandler.connect_dest, 'myproxy:8080')

        # check correct request message
        pHandler.s_out.seek(0)
        s_out = pHandler.s_out.read()
        self.assert_(s_out.find('GET http://creativecommons.org/ HTTP/1.0\r\n') == 0)
        self.assert_(s_out.find('Host: creativecommons.org') > 0)
        self.assert_(s_out.find('Connection: close') > 0)
        self.assert_(s_out.find('Proxy-connection: close') < 0)

        # check 1 message logged
        self.assertEqual(messagelog.mlog.currentId, 2)


    def testHandlerOverflow(self):

        backup = testcfg.cparser.get('messagelog', 'max_messagelog')
        # set maxresponse to 1KB so that sample.log will overflow
        testcfg.cparser.set('messagelog', 'max_messagelog', '1')
        try:
            pHandler = proxyhandler.testHandleMlog(testpath/'creative_commons.qlog')    # discard: ?
        finally:
            testcfg.cparser.set('messagelog', 'max_messagelog', backup)

        # check no log files are created
        self.assertEqual(messagelog.mlog.currentId, None)


    def testDiscarded(self):
        # discard: no response
        pHandler = proxyhandler.testHandleMlog(testpath/'empty_response.mlog')
        self.assertEqual(messagelog.mlog.currentId, None)

        # discard: 404
        pHandler = proxyhandler.testHandleMlog(testpath/'404.mlog')
        self.assertEqual(messagelog.mlog.currentId, None)


    def testException(self):

        fp1 = (testpath/'creative_commons.qlog').open('rb')
        fp1_req = MbReader(fp1)
        fp2_rsp = object()
        try:
            # note: fp2_rsp will gives us an exception when its read
            pHandler = proxyhandler.ProxyHandlerFixture(fp1_req, fp2_rsp,
                client_address=('127.0.0.1', 0), server=proxyhandler.TestServer())
            # note: ProxyHandler has caught the exception
            self.assertEqual(messagelog.mlog.currentId, None)
        finally:
            fp1.close()


if __name__ == '__main__':
    unittest.main()