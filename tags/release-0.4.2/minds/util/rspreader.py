"""Open multi block files and make file objects for the response parts.
"""

import cStringIO
import gzip
import httplib
import sys

from minds.util import fileutil
from minds.util import multiblockfile
from minds.util.multiblockfile import MbReader

# todo: readChunked return streaming interface? gzip does not work with streaming interface.

class RspReader:
  """ Open multi block files and make file objects for the response parts. """

  def __init__(self, fp, label):
    self.fp = fp
    self.label = label
    MbReader(fp).complete()     # skip block 1
    self.hdr_fp = MbReader(fp)  # first position on rsp header

  def _seek_response(self):
    self.hdr_fp.complete()
    self.hdr_fp = None
    self.rsp_fp = MbReader(self.fp)

  def read(self,*args):
    if self.hdr_fp:
        data = self.hdr_fp.read(*args)
        if data: return data
        self._seek_response()
    return self.rsp_fp.read(*args)

  def readline(self,*args):
    if self.hdr_fp:
        data = self.hdr_fp.readline(*args)
        if data: return data
        self._seek_response()
    return self.rsp_fp.readline(*args)

  def __iter__(self):
    return self

  def next(self):
    data = self.readline()
    if not data: raise StopIteration
    return data

  def close(self):
    self.fp.close()

  def __str__(self):
    return '<RspReader %s>' % self.label




def _readChunkLen(fp):
    """ May be 0 """

    line = fp.readline()
    if not line:
        raise IOError, 'Unexpected EOF'

    line = line.rstrip()
    try:
        clen = int(line,16)
    except ValueError, msg:
        raise IOError, 'Invalid chunk length: %s' % msg

    if clen < 0:
        raise IOError, 'Invalid chunk length: %s' % clen

    #print 'len=', line,' at', fp.tell()

    return clen



def readChunked(fp):
    """ return cStringIO buffer of the entire decoded message """

    buf = cStringIO.StringIO()
    while True:
        clen = _readChunkLen(fp)
        if clen == 0:                   # end of message marker
            break
        data = fp.read(clen)
        if len(data) < clen:
            raise IOError, 'EOF before reading chunk of %s characters' % clen
        eoc = fp.read(2)
        if eoc != '\r\n':
            raise IOError, 'Invalid end of chunk: %s' % eoc + str(fp.tell())
        buf.write(data)
    buf.seek(0)
    return buf



class ContentReader(fileutil.FileFilter):
  """ Return the content of the message log after applying HTTP
      content-encoding and transfer-encoding.

      Supported transfer-encoding: identity, chunked
      Supported content-encoding:  gzip
  """

  def __init__(self, log_fp, label):
    ''' log_fp is the file object to the message log (pos at 0) '''

    fileutil.FileFilter.__init__(self, None)
    self.log_fp = log_fp
    self.label = label

    # skip block 1
    MbReader(log_fp).complete()

    # parse header
    self.hdr_fp = MbReader(log_fp)
    filesoc = fileutil.FileSocket(self.hdr_fp)
    httpRsp = httplib.HTTPResponse(filesoc)
    httpRsp.begin()
    self.hdr_fp.complete()

    enc = httpRsp.getheader('content-encoding','').strip(' ').lower()
    te = httpRsp.getheader('transfer-encoding','').strip(' ').lower()

    # get content block
    self.fp = MbReader(log_fp)

    if te == 'chunked':
        self.fp = readChunked(self.fp)

    if enc == 'gzip' or enc == 'x-gzip':
        self.fp = gzip.GzipFile('content', 'r', fileobj=self.fp)

    elif (not enc) or (enc == 'identity'):
        pass

    else:
        # unknown encoding or multiple encoding
        raise IOError, 'Unsupported content-encoding: %s' % enc


  def __str__(self):
    return '<ContentReader %s>' % self.label



def openlog(path_or_fp):
    """ Open 'path_or_fp'.
        It can be a filename or file like object of a mlog file or a regular document.
        @returns - file object to the document's content.
    """

    if hasattr(path_or_fp, 'readlines'):
        fp = path_or_fp                 # treat as a file object
        try:
            path = fp.name
        except:
            path = '<?>'
    else:
        path = path_or_fp               # treat as a filename
        fp = file(path_or_fp,'rb')

    try:
        multiblockfile.MbReader(fp)
    except IOError, e:                  # don't work, treat as regular file
        #print e
        fp.seek(0)
        return fp
    else:                               # if no exception it is most likely mlog file
        fp.seek(0)
        return ContentReader(fp,path)



def main(argv):
    fp = openlog(argv[1])
    print fp.read()

if __name__ == '__main__':
    main(sys.argv)