"""Usage: store.py input_file output_file
"""

"""
MindRetrieve Weblib Data File Specification Version 0.6

MindRetrieve weblib data is an UTF-8 encoded text file (no other
encoding is supported as this time). The overall format is a block of
headers followed by a blank line and then the body similar to email and
HTTP messages. Each line of the body part represents a webpage or tag
item. Update to the weblib is appended as change records to the end of
the file. The entire weblib can be represented by a single file.

file            = headers BR body
headers         = *(header BR)
header          = field-name ":" [ field-value ]
field-name      = token
field-value     = DSV encoded value
body            = column-header BR *((data-line | comment-line | *SP) BR)
column-header   = column-name *( "|" column-name)
column-name     = token
comment-line    = "#" any string
data-line       = [change-prefix] (data-record | header)
change-prefix   = '[' YYYY-MM-DD 'T' HH:MM:SS 'Z]' SP ['r' | 'u' | 'h'] '!'
data-record     = ["@"] id *( "|" field-value)
BR              = CR | LF | CR LF
SP              = space characters


Note

* token is defined according to RFC 2616 Section 2.2.

* DSV encoded value is an unicode string with the characters "\", "|",
  CR and LF encoded as "\\", "\|", "\r" and "\n" respectively.

* There are two kind of data records, a webpage has a numeric id, while
  a tag has a numeric id prefixed by "@".

//* A record with the same id can appears multiple times in the data file.
//  The last record overwritten preceding records.

* A data-record preceded by a change-prefix denote update to the file.

* A record prefixed by "[ISO8601 time] r!" is a remove record. The item
  with the corresponding id is to be removed.

* A record prefixed by "[ISO8601 time] u!" is an update record. The item
  with the corresponding id is to be replaced.

* A record prefixed by "[ISO8601 time] h!" is an header update record. The
  header value is to be updated. There is no remove header record. A
  header value can be set to empty string however.

* The last line should always ended with BR. If the last line is not
  terminated with BR it is considered a corrupted record and must be
  discarded. Moreover never append change record to a corrupted record
  because the line break would be misplaced.

* The encoding header is defined for future extension only. Only UTF-8
  encoding is supported right now.


Discussions

[2005-12-01] This file is oringinal designed as a DSV file start with a
header line. New elements like change records have been introduced. The
extension is a stretch to the DSV design.

[2005-12-01] The way a record is updated is by appending the entire
record to the end of file. It may look like wasteful if there is only a
minor update. But the motivation is that the latest version of a record
can be found in one place. Thus it is possible to keep only the file
position of a record as index in memory.

[2005-12-01] The timestamp of the change record is in local time zone.
It is not guarantee to be in increasing order since users can change
time zone or reset their clock.

"""

import codecs
import datetime
import logging
import os
import re
import string
import StringIO
import sys
import threading

from minds.config import cfg
from minds import weblib
from minds.util import dateutil
from minds.util import dsv
from minds.weblib import util


log = logging.getLogger('wlib.store')



""" 2005-11-29 Discussion on the _interpretRecord() protocol

When an item is updated, instead of updating it in memory, the
writeXXX() method should be used. A change record is generated. Then
_interpretRecord() would build a new item from the change record and
assign it into wlib. The purpose of doing this is to force load() and
in-memory update to use the same code path. So that it minimize the
change that wlib reloaded would be different from the current wlib.

Several issue arised with this protocol.

* This is unintuitive to callers. wlib is open for in-memory update
  after all.

* The caller need to aware that the record it passes to writeXXX() is
essentially shredded after the call. It should query wlib to retrieve
the newly created record. This is again unintuitive, especially for
operations that requires a series of write.

* The webpage objects hold references to tag objects. If a tag is
rebuild, the references would be invalidated!

Is this protocol too problematic to use in practice?
"""

# TODO: header name definitionRFC 2616 2.
# The specification of header name observe the definition of token in RFC 2616 2.2 except the character '|' is not allowed.
#!#$%&'*+-.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ\^_`abcdefghijklmnopqrstuvwxyz|~
#'\s*[\!\#\$\%\&\'\*\+\-\.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ\\\^\_\`abcdefghijklmnopqrstuvwxyz\~]+\s*:'



# ------------------------------------------------------------------------
# Define writeFileMetaData for each OS
# Current only NTFS is supported

def nt_updateFileMetaData(item):
    from minds.weblib.win32 import ntfs_util
    p = ntfs_util.updateWebPage(item)
    if p:
        log.debug('updateFileMetaData: %s' % p)

def dummy_updateFileMetaData():
    pass

updateFileMetaData = dummy_updateFileMetaData

if os.name == 'nt':
    updateFileMetaData = nt_updateFileMetaData



def _getTimeStamp():
    now = datetime.datetime.utcnow()
    return dateutil.isoformat(now) + 'Z'


class Store(object):

    DEFAULT_FILENAME = 'weblib.dat'
    VERSION = '0.62'
    ENCODING = 'UTF-8'
    COLUMNS = [
    'id',           # 00
    'name',         # 01
    'description',  # 02
    'tagIds',       # 03
    'created',      # 04
    'modified',     # 05
    'lastused',     # 06
    'fetched',      # 07
    'flags',        # 08
    'url',          # 09
    ]
    NUM_COLUMN = len(COLUMNS)
    COLUMN_INDEX = dict(zip(map(string.lower, COLUMNS), xrange(NUM_COLUMN)))

    def __init__(self):
        self.lock = threading.RLock()

        self.pathname = cfg.getpath('weblib') / self.DEFAULT_FILENAME
        self.wlib = weblib.WebLibrary(self)
        self.writer = None
        self.reset()


    def reset(self):
        self.close()
        # reset running stat of current file
        self.num_wrecord = 0        # <---- TODO: save should update this
        self.num_rrecord = 0
        # reset filename?


    def _getWriter(self):
        """
        Return a writer object for updating. Use the cached writer if possible.
        """
        if self.writer:
            return self.writer
        if not os.path.isfile(self.pathname) or os.path.getsize(self.pathname) == 0:
            # file not exist? Use save() to write headers first
            log.info('Create weblib file: %s' % self.pathname)
            self.save()

        cur_version = self.wlib.headers.get('weblib-version','')
        if  cur_version != self.VERSION:
            # upgrade (or downgrade) weblib file
            # note that we must ensure the column header match what this version writes
            log.info('Upgrade weblib file existing verion=%s new version=%s' % (cur_version, self.VERSION))
            self.save()

# Note: There is a small issue about timing of calling save(). The sequence of
# events is depicted below:
#
#   writeTag()
#
#   line = ..change record..
#
#   _interpretRecord(line)      a record is added to wlib
#                               (any error is checked before _log())
#   _log()
#
#   _getWriter()
#
#   save()                      have the newly added record
#
#   write(line)                 write the change record
#
# This case the record to have written twice by the last two steps.

        fp = file(self.pathname, 'a+b')
        self.writer = codecs.getwriter(self.ENCODING)(fp,'replace')
        return self.writer


    def close(self):
        """ Close file. Also reset stats """
        if self.writer:
            self.writer.close()
            self.writer = None


    def __str__(self):
        if self.writer:
            mode = hasattr(self.writer,'mode') and self.writer.mode or '?'
        else:
            # writer closed
            mode = '_'
        nt = self.wlib and len(self.wlib.tags) or 'None'
        nw = self.wlib and len(self.wlib.webpages) or 'None'
        return 'Weblib file=%s(%s) #[%s,x%s] tags=#%s webpages=#%s' % (
            self.pathname,
            mode,
            self.num_wrecord,
            self.num_rrecord,
            nt,
            nw,
        )



    # ------------------------------------------------------------------------
    # load

    def load(self, pathname=None, fp=None):
        """
        Load self.pathname and build a WebLibrary.

        @param pathname - optional, override default pathname
        @param fp - optional, provide a ready make fp inplace of a disk file
        """
        self.lock.acquire()
        try:
            self.reset()

            if pathname:
                self.pathname = pathname
            if fp:
                use_disk_file = False
            else:
                use_disk_file = True
                if not os.path.isfile(self.pathname):
                    log.info('Weblib file not exist. Start from an empty library: %s' % self.pathname)
                    fp = StringIO.StringIO()    # dummy
                else:
                    log.info('Loading weblib from: %s' % self.pathname)
                    fp = file(self.pathname, 'rb')

            try:
                reader = codecs.getreader(self.ENCODING)(fp,'replace')
                linereader = enumerate(reader)

                self.wlib = weblib.WebLibrary(self)
                wlib = self.wlib

                # parse headers
                for lineno, line in linereader:
                    line = line.rstrip()
                    if not line: # end of headers?
                        break
                    self._interpretHeaderRecord(line)

                # parse row header
                row_headers = {}
                for lineno, line in linereader:
                    line = line.rstrip()
                    if not line or line.startswith('#'):
                        continue
                    row_headers = dsv.parse_header(lineno+1, line, self.COLUMNS)
                    break

                # data-records
                full_trace = False
                for lineno, line in linereader:
                    line = line.rstrip()
                    if not line or line.startswith('#'):
                        continue
                    try:
                        n = self._interpretRecord(line, row_headers)
                    except (KeyError, ValueError, AttributeError), e:
                        if not full_trace:
                            log.exception('Error parsing line %s' % (lineno+1,))
                            full_trace = True
                        else:
                            log.warn('Error parsing line %s: %s %s', lineno+1, str(e.__class__), e)
                    except Exception, e:
                        log.warn('Error Parsing line %s: %s %s', lineno+1, str(e.__class__), e)
                        raise

            finally:
                if use_disk_file:
                    fp.close()

            # For testing?
            # attach buffer fp to attach to self.writer for appending change records.
            if not use_disk_file:
                # seek to EOF
                fp.seek(0,2)
                # don't close it or you would this buffer
                self.writer = codecs.getwriter(self.ENCODING)(fp,'replace')

            # post-processing, convert tagIds to tag
            map(self._conv_tagid, wlib.webpages)
            wlib.category._compile()

        finally:
            self.lock.release()


    CHANGE_PREFIX = re.compile('\[([\d:\-T ]{19})Z?\] (\w)!')

    def _interpretRecord(self, line, row_headers):
        """
        Interpret the parsed record 'row'.
        Create, updated or remove WebPage or Tag records.

        @raise ValueError or KeyError for parsing problem
        @return - the item created or removed
        """
        mode = 'u'
        m = self.CHANGE_PREFIX.match(line)
        if m:
            timestamp = dateutil.parse_iso8601_date(m.group(1))
            mode = m.group(2)
            line =  line[m.end():]

        if mode == 'h':
            self._interpretHeaderRecord(line)

        else:
            fields = dsv.decode_fields(line)
            fields = map(string.strip, fields)
            row = dsv.RowObject(row_headers,fields)

            # TODO: field validation
            if row.id.startswith('@'):
                return self._interpretTagRecord(mode, row)
            else:
                return self._interpretWebPageRecord(mode, row)


    def _interpretHeaderRecord(self, line):
        pair = line.split(':',1)
        if len(pair) != 2:
            raise SyntaxError('Invalid header (format=name: value) - "%s"' % line)
        name = pair[0].strip().lower()
        value = pair[1].strip()
        # borrow dsv.decode_fields() to decode \ and line breaks.
        value = dsv.decode_fields(value)[0]
        self.wlib.setHeader(name,value)


    def _interpretTagRecord(self, mode, row):
        wlib = self.wlib

        id = int(row.id[1:])
        oldTag = wlib.tags.getById(id)

        if mode == 'r':
            if oldTag:
                wlib.tags.remove(oldTag)
            return oldTag
        else:
    # old logic say delete old tag and append a new version of tag.
    # This causes problem that references in webpage objects are invalidated.
    #
    #                if oldTag:
    #                    wlib.tags.remove(oldTag)
            if oldTag:
                # update object in-memory
                if oldTag.name != row.name:
                    wlib.tags.rename(oldTag, row.name)
                oldTag.description  = row.description
                oldTag.flags        = row.flags
                return oldTag
            else:
                tag = weblib.Tag(
                    id          = id,
                    name        = row.name,
                    description = row.description,
                    flags       = row.flags,
                )
                wlib.tags.append(tag)
                return tag


    def _interpretWebPageRecord(self, mode, row):
        wlib = self.wlib
        id = int(row.id)
        if row.tagids:
            s = row.tagids.replace('@','')
            tagids = [int(tid) for tid in s.split(',')]
        else:
            tagids = []

        oldItem = wlib.webpages.getById(id)

        if mode == 'r':
            if oldItem:
                wlib.webpages.remove(oldItem)
            return oldItem
        else:
            if oldItem:
                wlib.webpages.remove(oldItem)
            webpage = weblib.WebPage(
                id          = id,
                name        = row.name,
                description = row.description,
                tags        = [],
                flags       = row.flags,
                created     = row.created,
                modified    = row.modified,
                lastused    = row.lastused,
                fetched     = row.fetched,
                url         = row.url,
            )
            # should convert tagids to tags after reading the whole file??
            webpage.tagIds = tagids
            wlib.webpages.append(webpage)
            return webpage


    def _conv_tagid(self, item):
        """ Convert WebPage's tagids to list of Tag objects. """
        tags = [self.wlib.tags.getById(id) for id in item.tagIds]
        item.tags = filter(None, tags)
        # attribute no longer neeed. remove to avoid duplication
        del item.tagIds


    # ------------------------------------------------------------------------
    # Update

    def _log(self, line, flush):
        """ Write a log record to the data file """
        writer = self._getWriter()
        writer.write(line)
        writer.write('\r\n')
        if flush:
            writer.flush()


    def writeHeader(self, name, value, flush=True):
        """
        """
        self.lock.acquire()
        try:
            line = '[%s] h!%s' % (_getTimeStamp(), self._serialize_header(name, value))
            self._interpretRecord(line, self.COLUMN_INDEX)
            self._log(line, flush)

        finally:
            self.lock.release()


    def writeTag(self, tag, flush=True):
        """
        The tag can be a new or an existing tag.
        If tag.id is less than 0, a new id would be assigned.

        @param tag - the tag to be written. By design this item would
            be invalidated after this call. Use the new instance returned
            instead if necessary.

        @return an new instance of the tag written.

        Note: Special instruction to rename a tag
        ----------------------------------------------------------------
        Tags are indexed by name. We need the oldTag intact in order to
        update the index. To rename a tag, clone the it and assign it a
        new name. Then call writeTag() with the new instance.
        """
        self.lock.acquire()
        try:
            if tag.id < 0:
                tag.id = self.wlib.tags.acquireId()
            line = '[%s] u!%s' % (_getTimeStamp(), self._serialize_tag(tag))
            newTag = self._interpretRecord(line, self.COLUMN_INDEX)
            self._log(line, flush)

            # shred input tag
            if tag not in self.wlib.tags:   # this check make it even more hackish
                tag.__dict__.clear()        # TODO: this would only raise AttributeError for caller. Make better error message?

            return newTag

        finally:
            self.lock.release()


    def writeWebPage(self, webpage, flush=True):
        """
        The webpage can be a new or an existing item.
        If webpage.id is less than 0, an new id would be assigned.

        @param webpage - the webpage to be written. By design this item
            would be invalidated after this call. Use the new instance
            returned instead if necessary.

        @return an new instance of the webpage written.
        """
        self.lock.acquire()
        try:
            if webpage.id < 0:
                webpage.id = self.wlib.webpages.acquireId()
            line = '[%s] u!%s' % (_getTimeStamp(), self._serialize_webpage(webpage))
            newItem = self._interpretRecord(line, self.COLUMN_INDEX)
            self._conv_tagid(self.wlib.webpages.getById(newItem.id))
            self._log(line, flush)

            # shred the input webpage
            webpage.__dict__.clear()    # TODO: this would only raise AttributeError for caller. Make better error message?

            # 2005-12-20 TODO Review if this is the best place for this
            # If it is a file URL, try to save the meta data with the file also (if the OS support).
            if util.isFileURL(newItem.url):
                updateFileMetaData(newItem)

            return newItem

        finally:
            self.lock.release()


    def removeItem(self, item, flush=True):
        """
        Remove the item.

        @param item - a tag or webpage
        """
        self.lock.acquire()
        try:
            if isinstance(item, weblib.Tag):
                line = '[%s] r!@%s' % (_getTimeStamp(), item.id)
            else:
                line = '[%s] r!%s' % (_getTimeStamp(), item.id)
            self._interpretRecord(line, self.COLUMN_INDEX)
            self._log(line, flush)

        finally:
            self.lock.release()


    def flush(self):
        self.lock.acquire()
        try:
            if self.writer:
                self.writer.flush()
        finally:
            self.lock.release()


    # ------------------------------------------------------------------------
    # save

    def _serialize_header(self, name, value):
        return '%s: %s' % (name,dsv.encode_fields([value]))


    def _serialize_tag(self, tag):
        id = '@%d' % tag.id
        return dsv.encode_fields([
            id,
            tag.name,
            '',
            '',
            '',
            '',
            '',
            '',
            tag.flags,
            '',
        ])


    def _serialize_webpage(self, item):
        id = str(item.id)
        tagIds = ','.join(['@%s' % t.id for t in item.tags])
        return dsv.encode_fields([
            id              ,
            item.name       ,
            item.description,
            tagIds          ,
            item.created    ,
            item.modified   ,
            item.lastused   ,
            item.fetched    ,
            item.flags      ,
            item.url        ,
        ])


    def save(self, pathname=None, fp=None):
        """
        Output a snapshot of the weblib file.

        @param pathname - optional, override default pathname
        @param fp - optional, provide a ready make fp inplace of a disk file
        """
        self.lock.acquire()
        try:
            self.reset()

            # Save to pathname. Do not replace self.pathname however.
            if not pathname:
                pathname = self.pathname
            if fp:
                use_temp_file = False
            else:
                # First output to a temp file.
                # Then atomically replace the output file when done.
                use_temp_file = True
                tmp_pathname = pathname + '.tmp'
                backup_pathname = pathname + '.~'
                fp = file(tmp_pathname, 'wb')

            try:
                writer = codecs.getwriter(self.ENCODING)(fp,'replace')
                wlib = self.wlib

                # udpate timestamp
                wlib.setHeader('weblib-version', self.VERSION)
                wlib.setHeader('date', _getTimeStamp())

                # write headers
                _headers = wlib.headers.copy()
                for name in wlib.header_names:
                    if name not in _headers:
                        continue
                    # borrow dsv.encode_fields() to encode \ and line breaks.
                    v = dsv.encode_fields([])
                    writer.write(self._serialize_header(name,_headers[name]))
                    writer.write('\r\n')
                    del _headers[name]

                # write remaining headers not listed in wlib.header_names
                for n,v in _headers.items():
                    v = dsv.encode_fields([v])
                    writer.write('%s: %s\r\n' % (n,v))

                writer.write('\r\n')

                header = dsv.encode_fields(self.COLUMNS)
                writer.write(header)
                writer.write('\r\n')

                tags = [(tag.id, tag) for tag in wlib.tags]
                for id, tag in sorted(tags):
                    line = self._serialize_tag(tag)
                    writer.write(line)
                    writer.write('\r\n')

                webpages = [(page.id, page) for page in wlib.webpages]
                for id, page in sorted(webpages):
                    line = self._serialize_webpage(page)
                    writer.write(line)
                    writer.write('\r\n')

            finally:
                if use_temp_file:
                    fp.close()

            if use_temp_file:
#                print >>sys.stderr, 'v -', tmp_pathname
#                print >>sys.stderr, 'v -', pathname
#                print >>sys.stderr, 'v -', backup_pathname
                if os.path.isfile(pathname):
                    # backup existing file first
                    try:
                        # In posix, rename atomically replace old file with new
                        os.rename(pathname, backup_pathname)
                    except OSError:
                        # For Windows, delete before rename. Not atomic.
                        os.remove(backup_pathname)
                        os.rename(pathname, backup_pathname)
                os.rename(tmp_pathname, pathname)

        finally:
            self.lock.release()


# ------------------------------------------------------------------------

store_instance = None

def getStore(loadWeblib=True):
    global store_instance
    if not store_instance:
        store_instance = Store()
        if loadWeblib:
            store_instance.load()
    return store_instance

def getWeblib():
    return getStore().wlib


# ------------------------------------------------------------------------
# command line testing

def main(argv):
    if len(argv) < 2:
        print __doc__
        sys.exit(-1)

    pathname = argv[1]

    store = getStore(False)
    store.load(pathname)
    wlib = getWeblib()

    print 'Loaded %s\ncategory_description:\n%s\n#tags %s\n#webpages %s' % (
        argv[1], wlib.category.getDescription().encode('raw_unicode_escape')[:300], len(wlib.tags), len(wlib.webpages))

    newTag = weblib.Tag(name='hello tag')
    print >>sys.stderr, 'id', newTag.id
    newTag = store.writeTag(newTag)
    print >>sys.stderr, 'id', newTag.id
    store.removeItem(newTag)

    # save
    if len(argv) > 2:
        store.save(wlib, argv[2])


if __name__ == '__main__':
    main(sys.argv)