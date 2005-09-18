"""Usage:
"""

from cStringIO import StringIO

from minds.config import cfg
from minds.util import fileutil


# Discussion 2004/11/23
#
# The maxsize is the overall size of the message log. There is some
# advantage to put a cap on individual parts (e.g. request, response)
# rather than the the as a whole. For example, a request to upload a file
# may overflow maxsize but the response part can still be small document
# perfectly indexable. However such use case is deem uncommon and it is
# our desire to keep the design simple.


# Discussion 2004/11/23
#
# May introduce a maxcachesize (<= maxsize). If buffer size reach
# maxcachesize it show start writing to file to limit memory use. This
# will affect flush_*() and discard().


class CacheFile(fileutil.BoundedFile):
    """ A BoundedFile file object the cache the output in memory. Use
        write_xxx() methods to save content in file.
        Note: Get the currrent size in the cursize attribute (managed in
        fileutil.BoundedFile)
    """

    def __init__(self, maxsize):
        self.buf = StringIO()
        super(CacheFile, self).__init__(self.buf, maxsize)
        self.maxsize = maxsize
        self.cursize = 0
        self.overflow = False

    def write_mlog(self, id):
        """ save a message log '.mlog' """
        self._save(id+'.mlog')

    def write_qlog(self, id):
        """ save a queued log '.qlog' """
        self._save(id+'.qlog')

    def _save(self, filename):
        filepath = cfg.getpath('logs') / filename
        tmppath = filepath +'.tmp'
        fp = tmppath.open('wb')
        fp.write(self.buf.getvalue())
        fp.close()
        # write to a tmp file first and then rename to make it more atomic.
        tmppath.rename(filepath)

    def discard(self):
        self.buf = None
