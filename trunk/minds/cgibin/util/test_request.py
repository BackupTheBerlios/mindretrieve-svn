import StringIO
import sys
import unittest

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


if __name__ == '__main__':
    unittest.main()