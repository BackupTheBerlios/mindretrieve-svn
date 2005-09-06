"""Proxying web requests

1. HTTP requests - proxy and save message
2. HTTPS requests - tunnel through
3. Other requests - proxy using urllib

Based on the 'Tiny HTTP Proxy' by SUZUKI Hisao.
"""

import BaseHTTPServer, select, socket, urlparse
import cStringIO
import datetime
import logging
import os.path
import sys

from minds.config import cfg
from minds import cachefile
from minds import messagelog
from minds.util import multiblockfile
from minds.util import fileutil

# todo: ftp request
# todo: test _isHeaderEnd()

log = logging.getLogger('proxy')


class ProxyHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    rbufsize = 0                        # self.rfile Be unbuffered
    SELECT_TIMEOUT = 3
    MAX_IDLING = 20


    def __init__(self, request, client_address, server):
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, request, client_address,     server)


    def setup(self):
        BaseHTTPServer.BaseHTTPRequestHandler.setup(self)
        # the two attributes below are used in status report
        self.starttime = datetime.datetime.now()
        self.path = None
        self.server.setStatus(self)


    # See PooledHTTPServer.finish_request() for corresponding finish() method
    #def finish(self):
    #    BaseHTTPServer.BaseHTTPRequestHandler.finish(self)
    #    self.server.setStatus(None)


    def handle_one_request(self):
        """ Create logfp to log message. Wrap rfile to wiretap it. """

        messagelog.mlog.lastRequest = datetime.datetime.now()

        self.minfo = messagelog.MessageInfo()
        max_messagelog = cfg.getint('messagelog.max_messagelog', 2048)
        self.logfp = cachefile.CacheFile(max_messagelog*1024)

        try:
            # wiretap self.rfile using RecordFile; backup rfile in rfile0
            self.reqLogFp = multiblockfile.MbWriter(self.logfp)
            self.rfile0 = self.rfile
            self.rfile  = fileutil.RecordFile(self.rfile, self.reqLogFp)
            try:
                BaseHTTPServer.BaseHTTPRequestHandler.handle_one_request(self)
            finally:
                # disconnect rfile from RecordFile if it has not already been done.
                self.rfile = self.rfile0
        except:
            log.exception("Problem in handling request")

        if hasattr(self, 'command'):                    # note: command only assigned in BaseHTTPRequestHandler.handle_one_request()
            if self.command != 'CONNECT':
                messagelog.mlog.dispose(self.minfo, self.logfp, self.starttime)



    def do_GET(self):

    # record request properties

        self.minfo.setReq( self.command, self.path, self.headers)

    # verify request

        (scm, netloc, path, params, query, fragment) = urlparse.urlparse( self.path, 'http')

    # proxy connection

        soc = None
        try:
            try:
                soc = self._send_request(netloc, self.path, path, params, query)
                if not soc:
                    #already logged
                    #log.warn("Failed to connect to %s", netloc)
                    return
                rspBuf, header_size, bytes_received = self._transfer_data(soc)
                if header_size <= 0:
                    log.warn("No response from %s %s", netloc, path)
                    return

            except socket.error, e:
                # socket.error is common enough that we don't want to print the stack trace
                # e.g.
                #   (10053, 'Software caused connection abort')
                #   (10054, 'Connection reset by peer')
                log.warn('socket.error: %s' % str(e))
                return

        finally:
            try:
                if soc: soc.close()
            except Exception, e:
                log.exception('Unable to close outgoing socket')
            try:
                self.connection.close()
            except Exception, e:
                log.exception('Unable to close incoming socket')

    # interpret response

        self.minfo.parseRsp(rspBuf, bytes_received)

        if self.logfp.isOverflow():
            self.minfo.discard = True
            log.warn('logOverflow bytes received: %s', bytes_received)
            return

        ## ???
        #self.minfo._updateUriFs()


    def _send_request(self, netloc, fullpath, path, params, query):
        ''' Send request to remote server '''

        if self.server.next_proxy_netloc:                   # use next proxy?
            reqmsg = ["%s %s %s\r\n" % (                    # first line is http request
                self.command,
                fullpath,
                self.request_version)
            ]
            soc = self._connect_to( self.server.next_proxy_netloc)
        else:
            reqmsg = ["%s %s %s\r\n" % (                    # first line is http request
                self.command,
                urlparse.urlunparse(('', '', path, params, query, '')),
                self.request_version)
            ]
            soc = self._connect_to(netloc)

        if not soc: return None


        # headers
        self.headers['Connection'] = 'close'
        del self.headers['Proxy-Connection']
        for key, val in self.headers.items():
            key = key.capitalize()                  # header name are case-insensitive [RFC2616 4.2]
                                                    # however, Linksys admin seems to expect case sensitive header
                                                    # this is a hack to make it work with Linksys
                                                    # todo: should preserve whatever the browser sent
            reqmsg.append("%s: %s\r\n" % (key,val))

        # end of header
        reqmsg.append("\r\n")

        soc.send(''.join(reqmsg))
        return soc


    def _connect_to(self, netloc):
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        i = netloc.find(':')
        if i >= 0:
            host_port = netloc[:i], int(netloc[i+1:])
        else:
            host_port = netloc, 80
        try: soc.connect(host_port)
        except socket.error, arg:
            try: msg = arg[1]
            except: msg = arg
            self.send_error(404, msg)
            return None
        return soc


    def _transfer_data(self, soc):
        """ Transfers data across:

            browser  <-- self.connection -->  proxy  <-- soc -->  destination

            Returns rspBuf, header_size, bytes_received (content)
        """

        # these are data to keep track of the response stream
        rspBuf = cStringIO.StringIO()   # buffer until the end of header (\r\n\r\n) is found
        rspBuf_tail = ''                # header end may span two buffers, keep last 3 chars
        rspSize = 0                     # total count of response data read
        bodyPos = 0                     # position of response message body, 0 means not yet read

        proxy_pump = self._proxy_pump(self.connection, soc)

        # read until message body is found
        for cData, sData in proxy_pump:
            if cData:
                self.reqLogFp.write(cData)
            elif sData:
                bufPos = rspSize
                rspBuf.write(sData)
                rspSize += len(sData)
                bodyPos = self._findHeaderEnd(rspBuf_tail, sData, bufPos)
                if bodyPos:
                    break
                rspBuf_tail = sData[-3:]
                # todo: make the respone parsing line driven rather than buffer read driven?
                # No need for tricky _findHeaderEnd()
        else:
            # socket closed but header end still not found?
            bodyPos = rspSize

        # complete the request block
        self.reqLogFp.complete()

        # As a request/response protocol there should not be any more request data once response is sent.
        # But disconnect rfile from reqLogFp in anycase.
        self.rfile = self.rfile0

        # write response header in a new block
        fp = multiblockfile.MbWriter(self.logfp)
        rspBuf.seek(0)
        copyfileobj(rspBuf, fp, bodyPos)
        fp.complete()

        # write reposne body in a new block
        maxresponse = cfg.getint('messagelog.maxresponse', 1024)    # max maxresponse size in kb
        rspLogFp = multiblockfile.MbWriter(self.logfp)
        rspLogFp = fileutil.BoundedFile(rspLogFp, maxresponse*1024)
        rspBuf.seek(bodyPos)
        copyfileobj(rspBuf, rspLogFp, rspSize-bodyPos)

        # read the remaining message body (could be nothing)
        for cData, sData in proxy_pump:
            if cData:
                pass
            elif sData:
                rspSize += len(sData)
                rspLogFp.write(sData)

        rspLogFp.complete()

        rspBuf.seek(0)
        return rspBuf, bodyPos, rspSize - bodyPos



    def _proxy_pump(self, clientSoc, serverSoc):
        """ Generator to pump IO between client and server using select().
            generates (clientData, serverData);
            only one of clientData or serverData is not None
        """

        # todo: would it be simplier if it only generate response data, rather than either request or response data?
        # must make sure all socket are flushed

        iw = [clientSoc, serverSoc]
        count = 0
        while count < self.MAX_IDLING:
            count += 1
            (ins, _, exs) = select.select(iw, [], iw, self.SELECT_TIMEOUT)
            if exs: break   # ??? 09/03/04 what is exceptional conditions? raise exception? socket closed?

            if not ins:
                #print "\t" "idle", count
                continue

            for i in ins:
                data = i.recv(8192)
                if not data:
                    continue

                # reset counter only when data is received
                count = 0

                if i is serverSoc:
                    clientSoc.send(data)
                    yield None, data
                else:
                    # data from client
                    serverSoc.send(data)
                    yield data, None



    def _findHeaderEnd(self, last_tail, data, bufPos):
        """ Find the position of the start of message body.
            @param last_tail - the last 3 characters of the last
                   buffer, can be less than 3 characters
            @param bufPos - the beginning position of data (first byte 0)
        """

        # first scan the span between buffers
        # (it would be simplier to just join last_tail and data for find(),
        # but that would create a rather large buffer)
        if last_tail:
            span = last_tail + data[:3]     # last3 + first3
            index = span.find('\r\n\r\n')   # possible value -1..2
            if index >= 0:
                return (bufPos-3)+index+len('\r\n\r\n')

        # if not found, scan buffer
        index = data.find('\r\n\r\n')
        if index >= 0:
            return bufPos+index+len('\r\n\r\n')

        # header not found
        return 0


    def do_CONNECT(self):
        """ """

        # rfile already recorded the request line. But we will discard it.
        self.rfile = self.rfile0

        soc = self._connect_to(self.path)
        if not soc:
            #already logged
            #log.warn("Failed to connect to %s", self.path)
            return

        # just tunnel for now
        try:
            try:
                log.debug('Connect - %s', self.path)
                self.wfile.write(self.protocol_version +
                                 " 200 Connection established\r\n")
                self.wfile.write("Proxy-agent: %s\r\n" % self.version_string())
                self.wfile.write("\r\n")

                proxy_pump = self._proxy_pump(self.connection, soc)
                clen = 0
                for cData, sData in proxy_pump:
                    if sData:
                        clen += len(sData)
                #log.debug('Tunnel ended clen %s for %s', clen, self.path)

            except socket.error, e:
                # socket.error is common enough that we don't want to print the stack trace
                # e.g.
                #   (10053, 'Software caused connection abort')
                #   (10054, 'Connection reset by peer')
                log.warn('socket.error: %s' % str(e))
                return

        finally:
            soc.close()
            self.connection.close()



    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT  = do_GET
    do_DELETE=do_GET

    def log_message(self, format, *args):
        log.debug(format, *args)


def copyfileobj(fsrc, fdst, size):
    """ copy data of size from file-like object fsrc to file-like object fdst"""
    length=16*1024
    while size > 0:
        buf = fsrc.read(min(size,length))
        if not buf:
            break
        fdst.write(buf)
        size -= len(buf)



### cmdline testing ####################################################

from util.fileutil import FileSocket
from util.fileutil import aStringIO
from util.multiblockfile import MbReader
from util import patterns_tester
from util.rspreader import RspReader


class TestServer:
    def __init__(self, next_proxy=''):
        self.next_proxy_netloc = next_proxy

    def setStatus(self, obj):
        """ dummy method """
        pass


class ProxyHandlerFixture(ProxyHandler):

    """ Local version of ProxyHandler that uses local buffer instead of the network.

    Connection topology:

             c_in                 s_out
             --->    *********    --->
      Client         * proxy *          Server
             <---    *********    <---
             c_out                s_in


      c_in: caller provides input from client
      s_in: caller provides output form server
      s_out: recorded message sent to the server
      c_out: recorded message sent to the client

    """

    def __init__(self, c_in, s_in, client_address=('127.0.0.1', 0), server=TestServer()):
        self.s_out = aStringIO()
        self.c_out = aStringIO()
        self.client_soc = FileSocket(c_in, self.c_out)
        self.server_soc = FileSocket(s_in, self.s_out)
        self.server_netloc = ''
        ProxyHandler.__init__(self, self.client_soc, client_address, server)

    def _connect_to(self, netloc):
        """ Use FileSocket instead of making socket connection to server """
        self.connect_dest = netloc
        return self.server_soc

    def _proxy_pump(self, clientSoc, serverSoc):
        """ Need to override _proxy_pump() since select on FileSocket is not supported """
        while True:
            data = clientSoc.fin.read()
            if not data: break
            serverSoc.send(data)
            yield data, None
        while True:
            data = serverSoc.fin.read()
            if not data: break
            clientSoc.send(data)
            yield None, data



def testHandleMlog(filename, **args):
    """ Helper to build (and invoke) a ProxyHandlerFixture """

    fp1 = file(filename,'rb')
    fp1_req = MbReader(fp1)
    fp2_rsp = RspReader(file(filename, 'rb'), filename)
    try:
        return ProxyHandlerFixture(fp1_req, fp2_rsp, **args)
    finally:
        fp1.close()
        fp2_rsp.close()



def main(argv):
    """Usage: proxyhandler.py mlog_filename [proxy]"""

    if len(argv) <2:
        print main.__doc__
        sys.exit(-1)

    next_proxy = len(argv) > 2 and argv[2] or ''

    pHandler = testHandleMlog(argv[1], server=TestServer(next_proxy))

    # dump recorded message
    sys.stdout.write( patterns_tester.showFile( pHandler.s_out, 's_out [%s]' % pHandler.connect_dest))
    sys.stdout.write( patterns_tester.showFile( pHandler.c_out, 'c_out'))



if __name__ == '__main__':
    if sys.platform == "win32":     # set sys.stdout to binary mode for Windows
        import msvcrt
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    main(sys.argv)