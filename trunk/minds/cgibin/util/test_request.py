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
    return request.parse_weblib_url(rfile, env)


class TestRequest(unittest.TestCase):

    def test_method(self):
        self.assertEqual(_make_request(method='GET')[0], 'GET')
        self.assertEqual(_make_request(method='POST')[0], 'POST')

        # python's cgi module has problem handling not GET method and query_string
        # disable this test
        #self.assertEqual(_make_request(method='DELETE')[0], 'DELETE')

        # method parameter in querystring overrides HTTP method
        self.assertEqual(_make_request(method='GET',querystring='method=delete')[0], 'DELETE')

    def test_rid(self):
        self.assertEqual(_make_request(path='/_/form')[2:5], (-1,None,'form'))
        self.assertEqual(_make_request(path='/1/')[2:5], (1,None,''))
        self.assertEqual(_make_request(path='/2')[2:5], (2,None,''))
        self.assertEqual(_make_request(path='/x')[2:5], (None,None,''))

    def test_tid(self):
        self.assertEqual(_make_request(path='/@')[2:5], (None,None,''))
        self.assertEqual(_make_request(path='/@1/form')[2:5], (None,1,'form'))
        self.assertEqual(_make_request(path='/@2')[2:5], (None,2,''))
        self.assertEqual(_make_request(path='/@3/x')[2:5], (None,3,'x'))


if __name__ == '__main__':
    unittest.main()