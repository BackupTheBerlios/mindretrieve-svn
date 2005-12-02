import StringIO
import sys
import unittest
import urllib

from minds.cgibin.util import request

def _make_request(method='GET', path='/', querystring=''):
    rfile = StringIO.StringIO()
    env = {}
    env['REQUEST_METHOD'] = method
    env['PATH_INFO'] = path
    env['QUERY_STRING'] = querystring
    return request.WeblibRequest(rfile, env)


def _rid_request(method='GET', path='/', querystring=''):
    req = _make_request(method, path, querystring)
    return req.rid, req.path


def _tid_request(method='GET', path='/', querystring=''):
    req = _make_request(method, path, querystring)
    return req.tid, req.path


class TestRequest(unittest.TestCase):

    u_str = u'\u00f6'                       # small o with umlaut
    u8_str = u_str.encode('utf8')           # '\xc3\xb6'
    url_str = urllib.quote(u8_str)          # '%C3%B6'

    def test_method(self):
        self.assertEqual(_make_request(method='GET').method, 'GET')
        self.assertEqual(_make_request(method='POST').method, 'POST')

        # python's cgi module has problem handling not GET method and query_string
        # disable this test
        #self.assertEqual(_make_request(method='DELETE').method, 'DELETE')

        # method parameter in querystring overrides HTTP method
        self.assertEqual(_make_request(method='GET',querystring='method=delete').method, 'DELETE')

    def test_rid(self):
        self.assertEqual(_rid_request(path='/_/form'), (-1,'form'))
        self.assertEqual(_rid_request(path='/1/')    , (1,''))
        self.assertEqual(_rid_request(path='/2')     , (2,''))
        self.assertEqual(_rid_request(path='/x')     , (None,''))


    def test_tid(self):
        self.assertEqual(_tid_request(path='/@')      , (None,''))
        self.assertEqual(_tid_request(path='/@1/form'), (1,'form'))
        self.assertEqual(_tid_request(path='/@2')     , (2,''))
        self.assertEqual(_tid_request(path='/@3/x')   , (3,'x'))


    def test_param(self):
        req = _make_request(method='GET',querystring='aaa=&bbb=222&uuu='+self.url_str)
        self.assertEqual(req.param('aaa'),'')           # empty value is ok
        self.assertEqual(req.param('bbb'),'222')
        self.assertEqual(req.param('ccc'),'')           # non-exist param is ok
        self.assertEqual(req.param('uuu'),self.u_str)   # utf8 decoded
        self.assertTrue('aaa' in req.form)
        self.assertTrue('ccc' not in req.form)

        req = _make_request(method='GET',querystring='aaa=&bbb=222')


    def test_str(self):
        # make sure __str__() works, even if there are invalid unicode input
        req = _make_request(method='GET')
        s = unicode(req)
        self.assertTrue('GET' in s)

        s = unicode(_make_request(method='GET',querystring='aaa=111&bbb=222'))
        self.assertTrue('bbb' in s)
        self.assertTrue('222' in s)

        s = unicode(_make_request(method='GET',querystring='aaa='+self.url_str))
        self.assertTrue(self.u_str in s)        # decoded
        self.assertTrue('\\xc3' not in s)       # you won't find this

        broken_u8_str = self.u8_str[:1]
        s = unicode(_make_request(method='GET',querystring='aaa='+urllib.quote(broken_u8_str)))
        self.assertTrue(self.u_str not in s)    # can't decode
        self.assertTrue('\\xc3' in s)           # but it was escaped


if __name__ == '__main__':
    unittest.main()