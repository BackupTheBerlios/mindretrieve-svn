"""Usage: minds_lib.py input_file output_file
"""

import codecs
import logging
import os
import string
import sys
import threading

from minds.config import cfg
from minds import weblib
from minds.util import dsv


log = logging.getLogger('wlib.store')


COLUMNS = [
'id',           # 00
'name',         # 01
'description',  # 02
'tagIds',       # 03
'modified',     # 04
'lastused',     # 05
'cached',       # 06
'archived',     # 07
'flags',        # 08
'url',          # 09
]
NUM_COLUMN = len(COLUMNS)

"""
Minds weblib file specification

..designed..RFC2822...The weblib file is an UTF8 encoded text file.

file            = headers BR body
headers         = *(header BR)
header          = field-name ":" [ field-value ]
field-name      = token
field-value     = DSV encoded value
body            = column-header BR *((data-line | comment-line | *SP) BR)
column-header   = column-name *( "|" column-name)
column-name     = token
comment-line    = "#" any string
data-line       = ["r:"] data-record
data-record     = ["@"] id *( "|" field-value)
BR              = CR | LF | CR LF
SP              = space characters

Note
* token is defined according to RFC 2616 Section 2.2.
* DSV encoded value is an unicode string with the characters "\", "|",
  CR and LF encoded as "\\", "\|", "\r" and "\n" respectively.
* There are two kind of data records, a webpage have a numeric id, while
  a tag have a numeric id prefixed by "@".
* A record with the same id can appears multiple times in the data file.
  The last record overwritten preceding records.
* A data-record prefixed "r:" denotes the corresponding tag or webpage
  record is to be removed.

Discussions
* The way a record is updated ius by appending the entire record to the
  end of file. It may look like wasteful if there is only a minor
  update. But the motivation is that the latest version of a record can
  be found in one place. Alos it is possible to keep only the file
  position of a record as index in memory.
* How about change record for headers?

"""

# TODO: header name definitionRFC 2616 2.
# The specification of header name observe the definition of token in RFC 2616 2.2 except the character '|' is not allowed.
#!#$%&'*+-.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ\^_`abcdefghijklmnopqrstuvwxyz|~
#'\s*[\!\#\$\%\&\'\*\+\-\.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ\\\^\_\`abcdefghijklmnopqrstuvwxyz\~]+\s*:'


class Store(object):

    DEFAULT_FILENAME = 'weblib.dat'
    ENCODING = 'UTF8'

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


    def _getWriter(self, mode='a+b'):
        if not self.writer:
            fp = file(self.pathname, mode)
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
                fp = file(self.pathname, 'rb')

            try:
                reader = codecs.getreader(self.ENCODING)(fp,'replace')

                self.wlib = weblib.WebLibrary(self)
                wlib = self.wlib

                # read headers
                lineno = 0      # 0 based for headers
                for lineno, line in enumerate(reader):
                    line = line.rstrip()
                    if not line:
                        break
                    pair = line.split(':',1)
                    if len(pair) != 2:
                        raise SyntaxError('Header line should contain name and value separate by a colon (line %s)' % lineno)
                    name, value = map(string.strip, pair)
                    # force header name to be lower for now
                    name = name.lower()
                    # borrow dsv.decode_fields() to decode \ and line breaks.
                    value = dsv.decode_fields(value)[0]
                    if name not in wlib.header_names:
                        wlib.header_names.append(name)
                    wlib.headers[name] = value

                # read records
                lineno += 1     # adjust lineno to next line the reader is going to return
                lineno += 1     # make it one based

                # TODO: dsv.parse() not very intuitive, refactor

                for lineno, row in dsv.parse(reader, lineno):
                    try:
                        n = self._interpretRecord(row)
                        #print >>sys.stderr, '###DEBUG',n,str(self)
                    except (KeyError, ValueError, AttributeError), e:
                        log.warn('Error parsing line %s: %s %s', lineno, str(e.__class__), e)
                    except Exception, e:
                        log.warn('Error Parsing line %s: %s', lineno, str(e.__class__), e)
                        raise

            finally:
                if use_disk_file:
                    fp.close()

            if not use_disk_file:
                # seek to EOF
                fp.seek(0,2)
                # attach fp to self.writer for appending change records.
                # I guess this is just for testing and it won't get closed, right?
                self.writer = codecs.getwriter(self.ENCODING)(fp,'replace')

            # post-processing, convert tagIds to tag
            map(self._conv_tagid, wlib.webpages)
            wlib.category.compile()

        finally:
            self.lock.release()


    def _interpretRecord(self, row):
        """
        Interpret the parsed record 'row'.
        Create, updated or remove WebPage or Tag records.

        @raise ValueError or KeyError for parsing problem
        @return - the item created or removed
        """

        # mode w: write; r: remove
        if row.id.startswith('r:'):
            mode = 'r'
            row.id = row.id[2:]
            self.num_rrecord += 1
        else:
            # default is write
            mode = 'w'
            self.num_wrecord += 1

        wlib = self.wlib

        # TODO: field validation
        if row.id.startswith('@'):
            id = int(row.id[1:])

            oldTag = wlib.tags.getById(id)

            if mode == 'r':
                if oldTag:
                    wlib.tags.remove(oldTag)
                return oldTag
            else:
                if oldTag:
                    wlib.tags.remove(oldTag)
                tag = weblib.Tag(
                    id          = id,
                    name        = row.name,
                    description = row.description,
                    flags       = row.flags,
                )
                wlib.tags.append(tag)
                return tag

        else:
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
                    modified    = row.modified,
                    lastused    = row.lastused,
                    cached      = row.cached,
                    archived    = row.archived,
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

    # TODO HACK HACK!!!
    # this is a hack to build RowObject from by parsing a line
    # this module has not sufficiently deal with the column header in the data file and
    # the fact that it may different from the hardcoded COLUMN order of this version.
    _xheaders = dict(zip(map(string.lower, COLUMNS), range(len(COLUMNS))))
    def _xline_to_row(self, line):
        fields = dsv.decode_fields(line)
        fields = map(string.strip, fields)
        return dsv.RowObject(self._xheaders,fields)


    def _log(self, line, flush):
        """ Write a log record to the data file """
        writer = self._getWriter()
        writer.write(line)
        writer.write('\n')
        if flush:
            writer.flush()


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
            line = self._serialize_tag(tag)
            newTag = self._interpretRecord(self._xline_to_row(line))
            self._log(line, flush)

            # shed input tag
            tag.__dict__.clear()    # TODO: this would only raise AttributeError for caller. Make better error message?

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
            line = self._serialize_webpage(webpage)
            newItem = self._interpretRecord(self._xline_to_row(line))
            self._conv_tagid(self.wlib.webpages.getById(newItem.id))
            self._log(line, flush)

            # shed the input webpage
            webpage.__dict__.clear()    # TODO: this would only raise AttributeError for caller. Make better error message?

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
                line = 'r:@%s' % item.id
            else:
                line = 'r:%s' % item.id
            self._interpretRecord(self._xline_to_row(line))
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
            item.modified   ,
            item.lastused   ,
            item.cached     ,
            item.archived   ,
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
                fp = file(tmp_pathname, 'wb')

            try:
                writer = codecs.getwriter(self.ENCODING)(fp,'replace')
                wlib = self.wlib

                # write headers
                headers = wlib.headers.copy()
                for name in wlib.header_names:
                    if name not in headers:
                        continue
                    # borrow dsv.encode_fields() to encode \ and line breaks.
                    v = dsv.encode_fields([headers[name]])
                    writer.write('%s: %s\r\n' % (name,v))
                    del headers[name]

                # write remaining headers not listed in wlib.header_names
                for n,v in headers.items():
                    v = dsv.encode_fields([v])
                    writer.write('%s: %s\r\n' % (n,v))

                writer.write('\r\n')

                header = dsv.encode_fields(COLUMNS)
                writer.write(header)
                writer.write('\n')

                for tag in wlib.tags:
                    line = self._serialize_tag(tag)
                    writer.write(line)
                    writer.write('\n')

                for item in wlib.webpages:
                    line = self._serialize_webpage(item)
                    writer.write(line)
                    writer.write('\n')

            finally:
                if use_temp_file:
                    fp.close()

            if use_temp_file:
                try:
                    # this works atomically in Posix.
                    os.rename(tmp_pathname, pathname)
                except OSError:
                    # delete before rename for Windows. Not atomic.
                    os.remove(pathname)
                    os.rename(tmp_pathname, pathname)

        finally:
            self.lock.release()


# ------------------------------------------------------------------------

store_instance = None

def getStore():
    global store_instance
    if not store_instance:
        store_instance = Store()
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

    store = getStore()
    store.load(pathname)
    wlib = getWeblib()

    print 'Loaded %s\ncategory_description:\n%s\n#tags %s\n#webpages %s' % (
        argv[1], wlib.category.getDescription().encode('raw_unicode_escape')[:300], len(wlib.tags), len(wlib.webpages))

    newTag = weblib.Tag(name='hello tag')
    print >>sys.stderr, 'id', newTag.id
    store.writeItem(newTag)
    print >>sys.stderr, 'id', newTag.id
    store.removeItem(newTag)


    # save
    if len(argv) > 2:
        store.save(wlib, argv[2])


if __name__ == '__main__':
    main(sys.argv)