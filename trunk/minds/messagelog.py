"""Usage messagelog.py filename

Parse the message log 'filename'

The messagelog module asssists logging messages as it pass through the proxy.
Note that there can be simultaneous connections.

It also parses the message it has logged.
"""

import cStringIO
import datetime
import httplib
import logging
import mimetools
import os, os.path
import re
import threading
import sys

from config import cfg
from minds import urifs
from minds.util import fileutil
from minds.util import httputil
from minds.util import multiblockfile

### Message Id #########################################################

log = logging.getLogger('messagelog')
mlog = None



def getInt(s, default=None):
    try: return int(s)
    except: return default


class ParseMessageLogError(IOError):
    pass


class MessageInfo:
    ''' Represents the meta info of a HTTP message (request and response) '''

    def __init__(self):
        self.id         = None
        self.discard    = True

        # request attributes
        self.command    = ''
        self.req_path   = ''
        self.host       = ''
        self.host_noport= ''
        self.req_headers= {}

        # response attributes
        self.status     = 0
        self.rsp_headers= {}        # keys in lowercase
        self.clen       = 0
        self.ctype      = ''
        self.flags      = ''


    def setReq(self, command, path, headers):
        self.command  = command
        self.req_path = path
        self.req_headers = headers
        self.host, _ = urifs.parse(self.req_path)   # if req_path is path only, host=''
        self.host_noport = self.host.split(':')[0].lower()


    def parseRsp(self, rspBuf, bytes_received):
        ''' interpret http response and setup MessageInfo fields '''

        # 09/02/04 note: according to the documentation
        # httplib.HTTPResponse shouldn't instantiated directly by user.
        # Nor is the begin() call documented.
        filesoc = fileutil.FileSocket(rspBuf)
        httpRsp = httplib.HTTPResponse(filesoc)
        httpRsp.begin()

        self.status = httpRsp.status
        self.rsp_headers = dict(httpRsp.getheaders())
        self._parseHeaders(bytes_received)


    def _parseHeaders(self, bytes_received):

        # todo: should we make bytes_received matching a separate method from general parsing?

        # compare content-length with bytes received
        _truncated = False
        try:
            _clen = self.rsp_headers['content-length']
            self.clen = int(_clen)
            if self.clen != bytes_received:
                log.warn("message truncated - content-length: %s bytes received: %s - %s",
                    self.clen, bytes_received, self.req_path)
                _truncated = True
        except:
            self.clen = bytes_received

        # content-type
        self.ctype = self.rsp_headers.get('content-type','')
        if self.ctype:
            self.ctype = httputil.abbreviate_ctype(self.ctype)

        # cache-control
        items = self.rsp_headers.get('cache-control', '').split(',')
        items = [item.strip().lower() for item in items]
        _no_store = 'no-store' in items
        _no_cache = 'no-cache' in items

        # authorization
        _authorization = self.req_headers.has_key('authorization')

        self.flags = (_no_store and 'S' or '_') + (_no_cache and 'C' or '_') + \
            (_truncated     and 'T' or \
            (_authorization and 'A' or \
            (self.discard   and '_' or \
             '*')))

        # List of rules (and heuristics) to decide if the request should be discarded.
        # This is just simple filtering. More detail analysis would be applied during indexing.
        #
        # Note: some rationale of discarding
        #   discard: POST - non-idempotent method
        #   discard: 206 - Partial Content
        if                                          \
           (self.command == 'GET')              and \
           (self.status == 200)                 and \
           (self.ctype in ['html','txt'])       and \
           (not _authorization)                 and \
           (not _no_store)                      and \
           (not _truncated)                     and \
           (self.host_noport not in ['localhost']):
            self.discard = False


    @staticmethod
    def parseMessageLog(fp):
        """ Build a MessageInfo from a message log file. When this
            method returns, fp would be pointing at the start of content
            block.
        """
        minfo = MessageInfo()

        # parse request
        reqFp = multiblockfile.MbReader(fp)
        requestline = reqFp.readline()
        if not requestline:
            raise ParseMessageLogError('Request line is empty')
        words = requestline.split()
        if len(words) != 3:
            raise ParseMessageLogError('Invalid request line: %s' % requestline)

        req_headers = dict(mimetools.Message(reqFp))

        reqFp.complete()

        minfo.setReq(words[0], words[1], req_headers)


        # parse response
        rspFp = multiblockfile.MbReader(fp)
        if rspFp.clen == 0:
            raise ParseMessageLogError('no response')
        rspBuf = cStringIO.StringIO()
        rspBuf.write(rspFp.read())
        rspBuf.seek(0)
        rspFp.complete()


        # read len of content block
        cntFp = multiblockfile.MbReader(fp)


        # fill in other fields using parseRsp
        minfo.parseRsp(rspBuf, cntFp.clen)

        return minfo


    @staticmethod
    def _makeTestMinfo(rsp_header_list, bytes_received, method='GET', req_path='', req_headers=[], status='200'):
        """ Build a MessageInfo with baisc info """

        req_headers_dict = dict([(n.lower(),v) for n,v in req_headers])

        # construct response message
        msg = 'HTTP/1.0 %s OK\r\n' % status
        for name, val in rsp_header_list:
            msg += '%s: %s\r\n' % (name.lower(), val)
        msg += '\r\n'

        minfo = MessageInfo()
        minfo.setReq(method, req_path, req_headers_dict)
        minfo.parseRsp(cStringIO.StringIO(msg), bytes_received)
        return minfo


#    def _updateUriFs(self):
#        # 11/14/04 todo: this is some experimental code that doesn't do much right now
#        if not self.discard:
#            urifs.open(self.req_path, self.ctype, self.clen)


    def logmsg(self):
        return '%(id)9s,%(command)4s,%(status)-3s,%(ctype)-5s,%(clen)7s,%(flags)s,%(req_path)s' \
            % self.__dict__


    def __str__(self):
        return str(self.__dict__)



class MsgLogger(object):

    # match ddddddddd.mlog or ddddddddd.qlog
    log_pattern = re.compile('\d{1,9}\..log')

    def __init__(self):
        self.currentIdLock = threading.Lock()
        self.currentId = None
        self.lastIssued = None                      # last time an id is issued
        self.lastRequest = datetime.datetime.now()  # last activity, assinged by proxyhandler


    def _listdir(self, logdir):
        return os.listdir(logdir)


    def _findHighestId(self):
        """ Scan logs dir for files for the highest id.
            0 if no file found.
        """
        logdir = cfg.getPath('logs')
        files = filter(self.log_pattern.match, self._listdir(logdir))
        if not files:
            return 0
        files = [f.rjust(14) for f in files]
        top = max(files)
        return int(top.split('.')[0])


    def getId(self):
        """ return currentId and increment it by 1.
            Id is in the format of 9 digit string.
        """
        self.currentIdLock.acquire()
        try:
            if self.currentId == None:
                # This is going to be a long operation inside a
                # synchronization block. Everybody is going to wait
                # until the lazy initialization finish.
                self.currentId = self._findHighestId() + 1
                log.info('Initials currentId is %s', self.currentId)
            id = self.currentId
            self.currentId += 1
        finally:
            self.currentIdLock.release()
        self.lastIssued = datetime.datetime.now()
        return '%09d' % id


    def dispose(self, minfo, cachefp, starttime):
        """ Dispose the log in one or more format below
            mlog - for debugging, save if the mlog config is set
            qlog - queuing for indexing, save if minfo.discard is not set
        """

        mlogFlag = cfg.getboolean('messagelog.mlog', False)
        if not minfo.discard or mlogFlag:
            minfo.id = self.getId()

        if not minfo.discard:
            cachefp.write_qlog(minfo.id)

        if mlogFlag:
            cachefp.write_mlog(minfo.id)

        elapsed = datetime.datetime.now() - starttime
        log.debug('%3d.%02ds %s' % (elapsed.seconds, elapsed.microseconds/10000, minfo.logmsg()))


    @staticmethod
    def _getMsgLogPath(id):
        return os.path.join( cfg.getPath('logs'), id+'.qlog')

mlog = MsgLogger()



def main(argv):
    if len(argv) < 2:
        print __doc__
        sys.exit(-1)

    filename = argv[1]
    minfo = MessageInfo.parseMessageLog(file(filename,'rb'))
    print minfo.logmsg()


if __name__ == '__main__':
    main(sys.argv)
