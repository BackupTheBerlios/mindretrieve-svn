"""Usage: docarchive id filename

  Add the file as document #id
"""

import logging
import os, os.path, sys
import re
import StringIO
import threading
import zipfile

from minds.config import cfg


log = logging.getLogger('docarc')

class DocArchive(object):

    def __init__(self):
        self.currentIdLock = threading.Lock()
        self.currentId = None


    def getNewId(self):
        """ Return an unused new id. Id is in the format of 9 digit string. """

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
        return '%09d' % id


    arc_pattern = re.compile('\d{6}.zip')

    def _findHighestId(self):
        """ Scan db directories for files for the highest id.
            0 if no file found. Would throw exception if there is
            unrecoverable file corruption.
        """

        # scan for files under %dbdoc directory
        dbdoc = cfg.getPath('archive')
        files = filter(self.arc_pattern.match, os.listdir(dbdoc))
        if not files:
            return 0
        top_arc = max(files)

        # would throw BadZipfile if not a zip file
        zfile = zipfile.ZipFile(os.path.join(dbdoc, top_arc), 'r')

        # look in side the zip archive
        files = zfile.namelist()
        zfile.close()
        if files:
            top = max(files)
        else:
            # This is an odd case when there is a zip but nothing inside
            # (possibly some exception happened when adding to archive).
            # Highest really should be xxx000 - 1. Make it 000 here just
            # for simplicity.
            top = '000'

        if len(top) != 3 or not top.isdigit():
            raise IOError, 'Invalid file %s in %s' % (top, top_arc)

        return int(top_arc[:6] + top)   # would be a 9 digit id


    def _validateId(self, id):
        # id=123456789 -> db/doc/123456.zip/789
        if not id.isdigit() or len(id) != 9:
            raise ValueError, 'Invalid id: %s' % str(id)


    def get_archive(self, id, openedZipFile=None, closeIfNotNeeded=False):
        """ Open the zip archive file for the given id. openedZipfFile
            and closeIfNotNeeded parameters are used to reuse archive
            handle and reduce the number of times of open.

            @params openedZipfFile - if this corresponds to the archive
                to be opened, it used as return value instead. Caller
                can use 'is' to test its identity.
            @params closeIfNotNeeded - if openedZipFile is not the
                corresponding archive, close it if this parameter is
                True.

            openedZipFile is only closed when the whole operation can be
            completed successfully.
        """

        self._validateId(id)

        filename = id[:6] + '.zip'

        # check if openedZipFile is the corresponding archive
        if openedZipFile:
            openedFilename = os.path.split(openedZipFile.fp.name)[1]
            if openedFilename == filename:
                return openedZipFile

        # we need to open a new ZipFile
        pathname = os.path.join( cfg.getPath('archive'), filename)
        exists = os.path.exists(pathname)
        arc = zipfile.ZipFile(pathname, exists and 'a' or 'w', zipfile.ZIP_DEFLATED)

        if openedZipFile and closeIfNotNeeded:
            # Note: leave the closing of openedZipFile near the end when
            # exception is not likely to happen in order to guarantee
            # openedZipFile is only closed when the whole operation is
            # completed successfully. If this is done too early, exception
            # may be thrown subsequencely.
            try:
                openedZipFile.close()
            except:
                log.exception('Error when trying to close openedZipFile %s' % openedFilename)

        return arc


    def get_arc_document(self, id):
        """ Return the archive and a file object represents document
            #id. Please close the archive after use. Raise ? if id does
            not refer to an existing document.
        """
        arc = self.get_archive(id)
        try:
            fp = self.get_document(arc, id)
        except:
            arc.close()
            raise
        else:
            return arc, fp


    def get_document(self, arc, id):
        """
        """
        self._validateId(id)

        filename = id[-3:]
        # we trust caller that arc matches id[:6]

        # Why does ZipFile not provide a streaming api?
        # read() gets the whole file and we have to wrap it in StringIO
        content = arc.read(filename)
        return StringIO.StringIO(content)


    def add_document(self, arc, id, fp):
        """
        """
        self._validateId(id)
        filename = id[-3:]
        try:
            zipinfo = arc.getinfo(filename)
        except KeyError:    # good, filename not in arc
            pass
        else:               # expect KeyError; otherwise an entry is already there
            raise KeyError, 'Duplicated entry %s in %s' % (filename, arc.fp)
        arc.writestr(filename, fp.read())


docarc = DocArchive()



## cmdline testing #####################################################

def main(argv):
    if len(argv) < 3:
        print __doc__
        sys.exit(-1)

    from minds import proxy
    proxy.init('')

    id = argv[1]
    id = ('000000000' + id)[-9:]
    fp = file(argv[2])

    arc = docarc.get_archive(id)
    print 'Adding %s as document %s into %s' % (fp.name, id, arc.fp)
    try:
        docarc.add_document(arc, id, fp)
    finally:
        arc.close()


if __name__ == '__main__':
    main(sys.argv)