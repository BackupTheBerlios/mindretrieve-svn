"""
"""

import unittest

from config_help import cfg
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


if __name__ == '__main__':
    unittest.main()