""" HTTPServer base on BaseHTTPServer.HTTPServer with some custom behavior
"""

import BaseHTTPServer
import SimpleHTTPServer
import logging
import socket
import threading
import urlparse

from config import cfg
from minds.util import threadutil

log = logging.getLogger('httpserver')



class HTTPServer(BaseHTTPServer.HTTPServer):
    """ """

    def __init__(self, server_address, RequestHandlerClass):
        BaseHTTPServer.HTTPServer.__init__(self, server_address, RequestHandlerClass)


    def handle_error(self, request, client_address):
        log.exception('Exception happened during processing of request from %s', client_address)


    def verify_request(self, request, client_address):
        """ Restrict to local access only """

        src = client_address[0]
        if src != "127.0.0.1":
            log.error('Deny connection from %s' % src)
            return False

        dest = request.getsockname()[0]
        if dest != "127.0.0.1":
            log.error('Deny connection to nonlocal destination %s' % dest)
            return False

        return True


    def get_request(self):
        """ Replace the original blocking accept with a timeout accept
            and check for proxy.isShutdown() every few seconds.
        """
        from minds import proxy
        while True:
            if proxy.isShutdown():
                raise SystemExit, 0
            try:
                self.socket.settimeout(3)
                try:
                    (conn, address) = self.socket.accept()
                    conn.settimeout(None)   # conn inherited timeout setting from listening socket?
                    return (conn, address)
                finally:
                    self.socket.settimeout(None)
            except socket.timeout:
                pass



# todo: this is not quite generic PooledHTTPServer but with next hop proxy support for Minds proxy

class PooledHTTPServer(HTTPServer):
    """ Handle each request using thread pool """

    def __init__(self, server_address, RequestHandlerClass, numThreads):
        HTTPServer.__init__(self, server_address, RequestHandlerClass)
        self.pool = threadutil.PooledExecutor(numThreads, True)
        self.worker_status = [None] * numThreads
        self.next_proxy_netloc = ''
        self.read_config()


    def read_config(self):

        # reset only http_proxy here?!

        # setting in CERN httpd format (http://www.w3.org/Daemon/User/Proxies/ManyProxies.html)
        http_proxy = cfg.get('http.http_proxy', '')
        if not http_proxy:
            return

        (scm, netloc, path, params, query, fragment) = urlparse.urlparse( http_proxy, 'http')
        if scm != 'http' or not netloc:
            log.error('Invalid http_proxy="%s"', http_proxy)
            return
        self.next_proxy_netloc = netloc


    def report_config(self):
        return 'address=%s http_proxy="%s" #threads=%s' % \
            (self.server_address, self.next_proxy_netloc, len(self.pool.threads))


    def process_request(self, request, client_address):
        """ Process the request with a thread pool """

        task = threadutil.Runnable(
                             target=self.process_request_task,
                             args=(request, client_address))
        self.pool.execute(task)


    def process_request_task(self, request, client_address):
        """Same as in BaseServer but as a task to be run by a worker thread.
           In addition, exception handling is done here.
        """
        try:
            self.finish_request(request, client_address)
            self.close_request(request)
        except:
            self.handle_error(request, client_address)
            self.close_request(request)


    def finish_request(self, request, client_address):
        """Finish one request by instantiating RequestHandlerClass."""

        try:
            HTTPServer.finish_request(self, request, client_address)
        finally:
            # undo ProxyHandler.setup() here
            # It would be more logical to do this in ProxyHandler.finish()
            # Unfortunately the finish method() wasn't wrapped in finally clause
            self.setStatus(None)


    def setStatus(self, obj):
        """ Set worker thread local status """
        self.worker_status[threading.currentThread().id] = obj





def main():
    """ command line tester """

    print 'Launch HTTP port 8080 (#4)'
    server = PooledHTTPServer(('', 8080), SimpleHTTPServer.SimpleHTTPRequestHandler, 4)
    server.serve_forever()


if __name__ == '__main__':
    main()