"""Usage: docarchive [option] [id|filename]
    -r  read docid
    -a  add filename [not implemented]
"""

# todo: describe docarchive file format

# Note: id are generally added consecutively in chronical order.
# However, users are free to purge documents afterward. Therefore id
# does not necessary start from 0 nor are they necessary consecutive.


import logging
import os, os.path, sys
import re
import StringIO
import threading
import zipfile

from minds.config import cfg
from toollib import zipfile_single

log = logging.getLogger('docarc')



def parseId(id):
    """ Return arc_path, filename represents by id.
        e.g. id=123456789 -> $archive/123456.zip/789

        Raises KeyError if malformed
    """
    if not id.isdigit() or len(id) != 9:
        raise KeyError, 'Invalid id: %s' % str(id)

    apath = cfg.getPath('archive')
    return os.path.join(apath, id[:6]+'.zip'), id[6:]



def get_document(id):
    """ Return fp to the content of id.
        KeyError if arc_path or filename not exist.
    """

    arc_path, filename = parseId(id)

    if not os.path.exists(arc_path):
        raise KeyError, 'archive file does not exist %s' % arc_path

    zfile = zipfile_single.ZipFile(file(arc_path,'rb'), 'r')
    try:
        return StringIO.StringIO(zfile.read(filename))
    finally:
        zfile.close()



class IdCounter(object):

    def __init__(self):
        self.currentIdLock = threading.Lock()
        # archive status - beginId:endId
        #   None,None: uninitialized
        #   0,0      : no document
        #   0,1      : 1 document with id 0
        # ...and so on...
        self.beginId = None
        self.endId = None


    arc_pattern = re.compile('\d{6}.zip$')
    filename_pattern = re.compile('\d{3}$')

    def _findIdRange(self):
        """ Scan the $archive directory for zip files for the begin and end id. """

        apath = cfg.getPath('archive')
        files = filter(self.arc_pattern.match, os.listdir(apath))
        if not files:
            self.beginId = 0
            self.endId = 0
            return

        first_arc = min(files)
        last_arc  = max(files)

        first = self._findId(os.path.join(apath, first_arc), min)
        last  = self._findId(os.path.join(apath, last_arc ), max)

        self.beginId = int(first_arc[:6] + first)   # would be a 9 digit id
        self.endId   = int(last_arc[:6]  + last )   # would be a 9 digit id


    def _findId(self, path, min_or_max):
        """ return the min_or_max filename in path (as a 3 dight string) """

        zfile = zipfile.ZipFile(path, 'r')                      # would throw BadZipfile if not a zip file
        try:
            files = zfile.namelist()
            files = filter(self.filename_pattern.match, files)  # filter invalid filename
            if not files:
                # This is an odd case when there is a zip but nothing inside
                # (possibly some exception happened when adding to archive).
                # Highest really should be xxx000 - 1. Make it 000 here just
                # for simplicity.
                return '000'

            return min_or_max(files)

        finally:
            zfile.close()


    def getNewId(self):
        """ Return an unused new id. Id is in the format of 9 digit string. """

        self.currentIdLock.acquire()
        try:
            if self.endId == None:
                # This is going to be a long operation inside a
                # synchronization block. Everybody is going to wait
                # until the lazy initialization finish.
                self._findIdRange()
                log.info('Initial archive id range is %s:%s', self.beginId, self.endId)

            id = '%09d' % self.endId
            self.endId += 1
            return id

        finally:
            self.currentIdLock.release()


idCounter = IdCounter()



class ArchiveHandler(object):
    """ Optimize batch reading and writing by reusing opened zipfile if
        possible. Must call close() at the end.

        Parameter:
            mode - 'r' for read and 'w' for write
                   Internally use 'a' instead or 'w' if zip file exist (see zipfile.ZipFile)
    """

    def __init__(self, mode):
        if mode not in ['r','w']:
            raise ValueError, 'Invalid mode %s' % mode
        self.arc_path = None
        self.zfile = None
        self.mode = mode


    def _open(self, id):
        """ Return opened zfile, filename represents id """

        arc_path, filename = parseId(id)

        if self.arc_path:
            if self.arc_path == arc_path:       # same arc_path
                return self.zfile, filename     #   reuse opened zfile
            else:                               # different arc_path,
                self.close()                    #   must close previously opened zfile

        mode = self.mode
        if mode == 'w' and os.path.exists(arc_path):
            mode = 'a'
        self.zfile = zipfile.ZipFile(arc_path, self.mode, zipfile.ZIP_DEFLATED)
        self.arc_path = arc_path

        return self.zfile, filename


    def close(self):
        if self.zfile:
            self.zfile.close()
        self.zfile = None
        self.arc_path = None


    def add_document(self, id, fp):
        zfile, filename = self._open(id)
        try:                                        # check if filename is in archive
            zipinfo = self.zfile.getinfo(filename)
        except KeyError:                            # good, filename not in arc
            pass
        else:                                       # expect KeyError; otherwise an entry is already there
            raise KeyError, 'Duplicated entry %s in %s' % (filename, self.arc_path)

        self.zfile.writestr(filename, fp.read())



## cmdline testing #####################################################

def main(argv):

    from minds import proxy
    proxy.init(proxy.CONFIG_FILENAME)

    if len(argv) <= 1:
        print __doc__

    idCounter._findIdRange()
    print 'idRange [%s:%s]\n' % (idCounter.beginId, idCounter.endId)

    if len(argv) <= 1:
        sys.exit(-1)

    option = argv[1]
    if option == '-r':
        id = argv[2]
        id = ('000000000' + id)[-9:]
        arc_path, filename = parseId(id)
        print get_document(arc_path, filename).read()

    elif option == '-a':
        filename = argv[2]
        print 'not implemented'


if __name__ == '__main__':
    main(sys.argv)