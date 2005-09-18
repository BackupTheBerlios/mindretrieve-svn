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

    def test_parse_cgipath(self):
        handler = AppHTTPRequestHandlerFixture()
        self.assertEqual( handler.parse_cgipath(''),             (''    ,''     ,''   ))
        self.assertEqual( handler.parse_cgipath('/'),            ('/'   ,''     ,''   ))
        self.assertEqual( handler.parse_cgipath('/abc'),         ('/abc',''     ,''   ))
        self.assertEqual( handler.parse_cgipath('/abc/def'),     ('/abc','/def' ,''   ))
        self.assertEqual( handler.parse_cgipath('/abc?a=b'),     ('/abc',''     ,'a=b'))
        self.assertEqual( handler.parse_cgipath('/abc/?a=b'),    ('/abc','/'    ,'a=b'))
        self.assertEqual( handler.parse_cgipath('/abc/def?a=b'), ('/abc','/def' ,'a=b'))


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
        self.assertEqual(self.buf.getvalue(), 'HTTP/1.0 200 OK\r\n\r\n\r\n')


    def test_nodirective(self):
        self.fp.write(self.DATA1)
        self.fp.write(self.DATA2)
        self.assertEqual(self.buf.getvalue(), 'HTTP/1.0 200 OK\r\n' +
             self.DATA1 + self.DATA2)


    def test_status(self):
        self.fp.write('404 not found\r\n')
        self.fp.write(self.DATA1)
        self.fp.write(self.DATA2)
        self.assertEqual(self.buf.getvalue(), 'HTTP/1.0 404 not found\r\n'
            + self.DATA1 + self.DATA2)


    def test_location(self):
        self.fp.write('loCATion : http://abc.com/index.html\r\n')
        self.fp.write(self.DATA1)
        self.fp.write(self.DATA2)
        self.assertEqual(self.buf.getvalue(),
"""HTTP/1.0 302 Found\r
loCATion : http://abc.com/index.html\r
""" + \
            self.DATA1 + self.DATA2)



if __name__ == '__main__':
    unittest.main()