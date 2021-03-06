"""Usage: qmsg_processor options

The background queued message processor.
The following commands are available in interactive mode:

    -q  query status
    -i  index
    -t  transform
    -b  kick start background index
"""

import datetime
import logging
import re
import sys
import StringIO
import time

from minds.config import cfg
from minds import docarchive
from minds import messagelog
from minds import distillML
from minds import distillparse
from minds.util import httputil
from minds.util import rspreader

log = logging.getLogger('qmsg')

totalIndexed = -1   # number of document indexed (informational only, maybe staled)
archive_date = ''   # date of first document (informational only, maybe staled)

def getQueueStatus():
    """ Return the number of docs indexed and number of docs queued. """

    from minds import lucene_logic

    global totalIndexed, archive_date
    if totalIndexed < 0:
        indexpath = cfg.getpath('archiveindex')
        reader = lucene_logic.Reader(indexpath)
        totalIndexed = reader.reader.numDocs()
        # find out archive_date from the first 10 document
        for i in range(1,min(11,totalIndexed)):
            doc = reader.reader.document(i)
            d = doc.get('date')
            if d:
                archive_date = d
                break
        reader.close()
    logpath = cfg.getpath('logs')
    numQueued = len(_getQueuedText(logpath)) + len(_getQueuedLogs(logpath))
    return totalIndexed, archive_date, numQueued



QLOG_PATTERN = re.compile('\d{9}\.qlog')
QTXT_PATTERN = re.compile('\d{9}\.qtxt')

def _getQueuedLogs(logpath):
    """ Get the list of *.qlog. Sorted in ascending order """

    try:
        files = [p.name for p in logpath.listdir()]
    except:
        # assume baseDir does not exist
        return []
    qlogs = filter(QLOG_PATTERN.match, files)
    qlogs.sort()
    return qlogs



def _getQueuedText(logpath):
    """ Get the list of *.qtxt. Sorted in ascending order """

    try:
        files = [p.name for p in logpath.listdir()]
    except:
        # assume baseDir does not exist
        return []
    qtxts = filter(QTXT_PATTERN.match, files)
    qtxts.sort()
    return qtxts



def _shouldTransform(now, interval):
    """ if there is no activity for %interval minutes """
    return now - messagelog.mlog.lastRequest > datetime.timedelta(minutes=interval)



def _shouldIndex(now, logpath, queued):
    """ Checks queue status. Returns a flag indicates whether background
        indexing should be invoked.

        @param now - current time (e.g. from datetime.datetime.now())
        @param queued - list of queued files (e.g. from _getQueuedLogs() )

        @return - detail return code
         0: do not index
         1: index (numDoc has met)
         2: index (max_interval has reached)
        -1: index (fail to evaluate time elapsed since lastIssued and numDoc has met)
        -2: index (fail to evaluete time elapsed since first queued)
    """

    numQueued = len(queued)
    if numQueued < 1:
        return 0

    # todo: add some logging for the decision process?

    # Read config. Note interval and max_interval are compared against
    # different base. See rule 1 & 2 for detail.
    numDoc       = cfg.getint('indexing.numDoc',50)
    interval     = datetime.timedelta( seconds=cfg.getint('indexing.interval',3      )*60 )
    max_interval = datetime.timedelta( seconds=cfg.getint('indexing.max_interval',360)*60 )


    # Rule 1. time elapsed since 'lastIssued' > 'interval' and has 'numDoc'
    lastIssued = messagelog.mlog.lastIssued
    if lastIssued == None: lastIssued = now - interval

    # Detail of rule 1's 'now' v.s. 'lastIssued' timing chart
    #
    #
    #   -interval     lastIssued     +interval
    #       |             |              |
    # ------+-------------+--------------+---------
    #    ^        ^               ^           ^
    #    |        |               |           |
    #    |        |               |       1. Quiet enough. Check numDoc
    #    |        |               |
    #    |        |         2. Has recent activity. Wait till 1.
    #    |        |
    #    |  3. Assume a very recent activity just happened after 'now' is set. Wait till 1.
    #    |
    # 4. lastIssued is too far into the future.
    #    This cannot be explained by 3.
    #    Assume the clock has been reset to earily time.
    #    Check numDoc now to avoid stagnant.
    #
    #
    # Note: 3 and 4 are unusual scenarios (with lastIssued in the future w.r.t now)


    if now >= lastIssued + interval and numQueued >= numDoc:    # case 1
        return 1
    if now + interval < lastIssued and numQueued >= numDoc:     # case 4
        return -1


    # Rule 2. time elapsed since first queued > 'max_interval'
    firstfile = min(queued)
    mtime = (logpath/firstfile).mtime
    d0 = datetime.datetime.fromtimestamp(mtime)
    elapsed = now - d0
    if elapsed.days < 0:
        return -2           # if elapsed < 0, the system clock must has been reset
    if elapsed >= max_interval:
        return 2

    return 0



def backgroundIndexTask(forceIndex=False):
    """ This is the main task of qmsg_processor. The tasks has two phrases.

    I. Transform phrase

        Parse *.qlog
        Filtered out unwanted docs
        Transform into *.qtxt
        Add into archive

        Suspense this process when user access proxy.


    II. Index phrase

        Add *.qtxt into index
        Optimize

        During optimize, block out searching.
        (12/03/04 note: Due to GIL and PyLucene implementation, it
        will actually block out every thing, including proxy.)

        Returns transformed, index, discarded
    """

    interval= cfg.getint('indexing.interval',3)
    logpath = cfg.getpath('logs')
    now = datetime.datetime.now()

    transformed = 0
    discarded_t = 0
    indexed = 0
    discarded_i = 0

    qlogs = _getQueuedLogs(logpath)
    if forceIndex or _shouldTransform(now, interval):
        transformed, discarded_t = TransformProcess().run(logpath, qlogs)

    qtxts = _getQueuedText(logpath)
    if forceIndex or \
        (_shouldTransform(now, interval) and _shouldIndex(now, logpath, qtxts)): # first check is if there is new activity
        indexed, discarded_i = IndexProcess().run(logpath, qtxts)

    return transformed, indexed, discarded_t + discarded_i



# default value maybe used in unit testing
g_maxuri = 10
g_archive_interval = 1


class TransformProcess(object):

    def __init__(self, removeQlog=True, backupQlog=False):
        self.num_transformed = 0
        self.num_discarded = 0
        self.backupQlog = backupQlog        # todo: remove this switch in the future
        self.removeQlog = removeQlog


    def run(self, logpath, qlogs):
        """ Transform documents in qlogs. Returns number of transformed, discarded """

        qlogs = filter(None, qlogs)         # defensively remove '' entries. Otherwise path would point to logpath for '' entry.
        if not qlogs: return 0, 0

        log.info('Transforming %s documents starting from %s' % (len(qlogs), qlogs[0]))

        # initialize configuration parameters
        global g_maxuri, g_archive_interval
        g_maxuri = cfg.getint('messagelog.maxuri',1024)
        g_archive_interval = cfg.getint('indexing.archive_interval',1)

        for filename in qlogs:              # main loop

            inpath = logpath/filename
            outpath = inpath.splitext()[0] + '.qtxt'

            transformed = False             # transform
            try:
                transformed = self.transformDoc(inpath, outpath)
            except messagelog.ParseMessageLogError, e:
                log.warn('Error %s: %s', str(e), filename)
            except:
                log.exception('Error transforming: %s', filename)

            # postprocess qlog
            try:
                if self.backupQlog:
                    savepath = logpath/'tmp'/filename
                    if savepath.exists(): savepath.remove()
                    inpath.rename(savepath)

                # whether it is successfully transformed or not, remove the
                # input file to avoid build up. Hopefully the error message is
                # informative enough for diagnosis.
                elif self.removeQlog:
                    inpath.remove()

            except OSError:
                log.exception('Error in postprocess of %s', inpath)

            if transformed:
                self.num_transformed += 1
            else:
                self.num_discarded += 1

        log.info('Transformed %s; Discarded %s', self.num_transformed, self.num_discarded)

        return self.num_transformed, self.num_discarded



    def transformDoc(self, inpath, outpath):
        """ Parse a message log file. Filter unwant document and transform it.
            File specified by outpath is only created when this success.

            @return whether the document is transformed.
        """

        dt = datetime.datetime.utcfromtimestamp(inpath.mtime)
        timestamp = _formatTimestamp(dt)

        rfile = inpath.open('rb')
        try:
            minfo = messagelog.MessageInfo.parseMessageLog(rfile)
            if minfo.discard:
                # these should be filtered in logging phrase, but double
                # check here perhaps for logs collected from other sources.
                log.info('discard %s %s - %s' % (inpath.name, minfo.flags, minfo.req_path))
                return False

            meta = _extract_meta(minfo, timestamp)

            # simple filtering
            if (minfo.status < 200) or (300 <= minfo.status):
                return False
            if minfo.ctype != 'html' and minfo.ctype != 'txt':
                return False

            rfile.seek(0)
            contentFp = rspreader.ContentReader(rfile, inpath)

            discard = False
            wfile = outpath.open('wb')
            try:
                if minfo.ctype == 'html':
                    result = distillML.distill(contentFp, wfile, meta=meta)
                else:
                    result = distillML.distillTxt(contentFp, wfile, meta=meta)
                if result != 0:
                    log.info('discard %s %s - %s' % (inpath.name, str(result), minfo.req_path))
                    discard = True
            finally:
                wfile.close()

        finally:
            rfile.close()

        if discard:
            outpath.remove()    # remove unwanted output
            return False
        else:
            log.debug('transformed %s (%s) - %s', outpath.name, meta.get('encoding','?'), minfo.req_path)

        return True



def _formatTimestamp(dt):
    """ format time stamp """
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')



def _parseTimestamp(s):
    """ parse time stamp in the format of yyyy-mm-ddThh:mm:ssZ """
    if len(s) != 20:
        raise ValueError, 'Not a 20 char timestamp: "%s"' % s
    return datetime.datetime(
        int(s[:4]), int(s[5:7]), int(s[8:10]),
        hour=int(s[11:13]), minute=int(s[14:16]), second=int(s[17:19])
    )



def _extract_meta(minfo, timestamp):
    """ Extract some meta data from the response header, including

        uri - from request path
        date - from timestamp
        ETag or last-modified - from http header
        content-type - from http header (for its charset)

        The dictionary is case-sensitive and keys are in lowercase.
    """

    meta = {}
    uri = httputil.canonicalize(minfo.req_path)
    if len(uri) > g_maxuri:
        uri = uri[:g_maxuri] + '...'
    meta = {'uri': uri}                                                 # uri
    meta['date'] = timestamp                                            # date

    # Include either etag or last-modified
    # Otherwise use content-length as a weak ETag
    etag = minfo.rsp_headers.get('etag','')
    if etag:
        meta['etag'] = etag                                             # ETag
    else:
        last_modified = minfo.rsp_headers.get('last-modified','')
        if last_modified:
            meta['last-modified'] = last_modified                       # last-modified
        else:
            meta['etag'] = "W/%s" % minfo.clen                          # use clen as a weak etag

    meta['content-type'] = minfo.rsp_headers.get('content-type','')     # content-type

    meta['referer'] = minfo.req_headers.get('referer','')               # referer (from request)

    return meta



class IndexProcess(object):

    def __init__(self):
        self.writer = None
        self.searcher = None
        self.arcHandler = None
        self.freshdocs = {}
        self.numIndexed = 0
        self.numDiscarded = 0


    def _open(self):
        from minds import lucene_logic
        indexpath = cfg.getpath('archiveindex')
        self.writer = lucene_logic.Writer(indexpath)
        self.searcher = lucene_logic.Searcher(pathname=indexpath)


    def _finish(self):
        if self.writer:     self.writer.close()
        if self.arcHandler: self.arcHandler.close()
        if self.searcher:   self.searcher.close()


    def run(self, logpath, qtxts):
        qtxts = filter(None, qtxts)         # defensively remove '' entries. Otherwise path would point to logpath for '' entry.
        if not qtxts: return 0, 0

        log.info('Indexing %s documents starting from %s' % (len(qtxts), qtxts[0]))

        self._open()
        self.arcHandler = docarchive.ArchiveHandler('w')
        try:
            for filename in qtxts:
                filepath = logpath/filename
                try:
                    if self.indexDoc(filepath):
                        self.numIndexed += 1
                    else:
                        self.numDiscarded += 1
                except:
                    self.numDiscarded += 1
                    log.exception('Failed in indexDoc: %s', filepath)

                try:
                    filepath.remove()   # remove whether it is success or not
                except:
                    log.exception('Error removing %s', filepath)

        finally:
            try:
                log.info('Optimize and close index')
                self._finish()
            except: # do not throw error in finally clause
                log.exception('Error trying to close index state')

        global totalIndexed
        totalIndexed = self.writer.writer.docCount()    # already closed???

        log.info("indexed #%s discarded #%s" % (self.numIndexed, self.numDiscarded))
        return self.numIndexed, self.numDiscarded



    def indexDoc(self, filepath):

        fp = filepath.open('rb')
        try:
            meta, content = distillparse.parseDistillML(fp, distillparse.writeHeader)
            uri = meta['uri']                               # if there is no uri, throw an exception and discard this doc

            # check index to see if document already indexed
            result = self._searchForArchived(uri, meta)
            if result:
                log.info('discard %s archived(%s) - %s' % (filepath.name, result, uri))
                return False

            # add this document in the archive
            fp.seek(0)
            id = docarchive.idCounter.getNewId()
            self.arcHandler.add_document(id, fp)

            # add this document into the index
            self.writer.addDocument(id, meta, content)

            # remember it in freshly added document
            # note if there are existing uri, it will be overwritten by the new one
            self.freshdocs[uri] = meta

            log.info('%s -> %s' % (filepath.name, id))

        finally:
            fp.close()

        return True



    def _searchForArchived(self, uri, meta1):

        meta0 = self.freshdocs.get(uri,None)            # first, search the freshdocs
                                                        # this table is separately maintain by the IndexProcess
                                                        # because the docs are not yet visible via the index searcher.
        if not meta0:
            hits = self.searcher.searchLast(uri)        # next, search the index
            if not hits or hits.length() <= 0:
                return None                             # not found, it is not indexed

            doc0  = hits.doc(0)                         # use the latest document found
            meta0 = {
                'uri': doc0.get('uri'),
                'date': doc0.get('date'),
                'etag': doc0.get('etag'),
            }

        return isSimilar(meta0, meta1)



def isSimilar(meta0, meta1):
    """ Search index for similar versions of the document. This is used
    to prevent repeatly archiving similar version of the same URI. The
    rule used in the match are:

    1. If etag or last-modified match.
    2. If a document is archived within the last 'archive_interval' days.

    todo: Use statistical algorithm to compute similarity.

    Note: only the most recently archived document is used in comparison.

    @returns
        description - if similar document exists.
        None - if no document found.
        False - if no similar document exists.
    """

    # last document
    date0 = meta0.get('date','')
    etag0 = meta0.get('etag','')
    if not etag0:
        etag0 = meta0.get('last-modified','')

    # this document
    date1 = meta1.get('date','')
    etag1 = meta1.get('etag','')
    if not etag1:
        etag1 = meta1.get('last-modified','')

    # same version exist?
    if etag1 == etag0:
        return 'v=%s' % etag1

    # within certain interval?
    interval = datetime.timedelta(days=g_archive_interval)

    try:
        dt0 = _parseTimestamp(date0)
    except:                                                         # tolerant to small error in existing documents
        dt0 = datetime.datetime.utcfromtimestamp(0)
        log.warning('Invalid timestamp: %s - %s', date0, meta0['uri'])

    try:
        dt1 = _parseTimestamp(date1)
    except:
        log.exception('Unable to parse timestamp dt0=%s dt1=%s' % (date0, date1))
        return 'error parse timestamp'

    if (dt1 - dt0) < interval:
        return 'last=%s' % date0

    return False





# ----------------------------------------------------------------------
# Command line utility

def main(argv):
    if len(argv) <= 1:
        print __doc__
        sys.exit(-1)

    option = argv[1]

    if option == '-q':
        print 'getQueueStatus numIndexed %s date %s numQueued %s' % getQueueStatus()

    elif option == '-t':
        logpath = cfg.getpath('logs')
        qlogs = _getQueuedLogs(logpath)
        transformed, discarded = TransformProcess().run(logpath, qlogs)
        print transformed, discarded

    elif option == '-i':
        logpath  = cfg.getpath('logs')
        qtxts = _getQueuedText(logpath)
        indexed, discarded = IndexProcess().run(logpath, qtxts)
        print indexed, discarded

    elif option == '-b':
        messagelog.mlog.lastRequest = datetime.datetime(1990,1,1)   # enable _shouldTransform
        result = backgroundIndexTask()
        print result


if __name__ == '__main__':
    main(sys.argv)