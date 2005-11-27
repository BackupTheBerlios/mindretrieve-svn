"""
"""

import StringIO
import unittest

from minds.safe_config import cfg as testcfg
from minds import app_httpserver


class AppHTTPRequestHandlerFixture(app_httpserver.AppHTTPRequestHandler):
    def __init__(self):
        pass


class TestAppHTTPRequestHandler(unittest.TestCase):

    def _test_lookup(self, url, expected):
        handler = AppHTTPRequestHandlerFixture()
        self.assertEqual(handler._lookup_cgi(url), expected)


    def test_lookup_cgi(self):
        from minds.cgibin import home
        from minds.cgibin import config
        from minds.cgibin import weblibMultiForm
        self._test_lookup('',                       (home, '/', '', ''))
        self._test_lookup('/',                      (home, '/', '', ''))
        self._test_lookup('/config/item?1',         (config, '/config', '/item', '1'))
        self._test_lookup('/weblib/multiform/100',  (weblibMultiForm, '/weblib/multiform', '/100', ''))



class TestMisc(unittest.TestCase):

    def test_convertPath2Module1(self):
        self.assertEqual(
            app_httpserver._convertPath2Module(r'./minds\admin\tmpl/home.html'),
            ('minds.admin.tmpl.home','home'),
        )

    def test_convertPath2Module2(self):
        self.assertEqual(
            app_httpserver._convertPath2Module(r'./minds\admin\snoop'),
            ('minds.admin.snoop','snoop'),
        )

    def test_convertPath2Module3(self):
        self.assertEqual(
            app_httpserver._convertPath2Module(r'/minds/admin/snoop.py'),
            ('minds.admin.snoop','snoop'),
        )



class TestCGIFileFilter(unittest.TestCase):

    DATA1 = """date:04/19/05\r
\r
line1
line2
"""
    DATA2 = """line3
line4"""

    def setUp(self):
        self.buf = StringIO.StringIO()
        self.fp = app_httpserver.CGIFileFilter(self.buf)


    def test1(self):
        self.fp.write('\r\n\r\n')
        self.fp.flush()
        self.assertEqual(self.buf.getvalue(), 'HTTP/1.0 200 OK\r\n\r\n\r\n')


    def test_nodirective(self):
        self.fp.write(self.DATA1)
        self.fp.write(self.DATA2)
        self.fp.flush()
        self.assertEqual(self.buf.getvalue(), 'HTTP/1.0 200 OK\r\n' +
             self.DATA1 + self.DATA2)


    def test_status(self):
        self.fp.write('404 not found\r\n')
        self.fp.write(self.DATA1)
        self.fp.write(self.DATA2)
        self.fp.flush()
        self.assertEqual(self.buf.getvalue(), 'HTTP/1.0 404 not found\r\n'
            + self.DATA1 + self.DATA2)


    def test_location(self):
        self.fp.write('loCATion : http://abc.com/index.html\r\n')
        self.fp.write(self.DATA1)
        self.fp.write(self.DATA2)
        self.fp.flush()
        self.assertEqual(self.buf.getvalue(),
"""HTTP/1.0 302 Found\r
loCATion : http://abc.com/index.html\r
""" + \
            self.DATA1 + self.DATA2)


    def test_states(self):
        # verify CGIFileFilter has gone through each state
        self.assertEqual(self.fp.state, self.fp.INIT)

        self.fp.write('200 ok\r\n\r\n')
        self.assertEqual(self.fp.state, self.fp.BUFFER)

        self.fp.write('.'*(self.fp.MAX_BUFFER+1))
        self.assertEqual(self.fp.state, self.fp.SENT)

        buf_size = len(self.buf.getvalue())
        self.assert_(buf_size > self.fp.MAX_BUFFER+1)   # some HTTP info + content

        # still accepting output at SENT state
        self.fp.write('.')
        self.assertEqual(len(self.buf.getvalue()), buf_size+1)


    def test_buffer(self):
        # verify data is buffered until flush
        self.fp.write('200 ok\r\n\r\n')
        self.fp.write('.')
        self.assertEqual(len(self.buf.getvalue()), 0)

        self.fp.flush()
        self.assert_(len(self.buf.getvalue()) > 0)



if __name__ == '__main__':
    unittest.main()