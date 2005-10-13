"""Usage: minds_lib.py input_file output_file
"""

import codecs
import logging
import string
import sys

from minds.config import cfg
from minds import weblib
from minds.util import dsv


log = logging.getLogger('weblib.mnd')


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



def load(rstream):
    wlib = weblib.WebLibrary()
    encoding = 'UTF8'

    reader = codecs.getreader(encoding)(rstream,'replace')
    lineno = 0
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
        wlib.header_names.append(name)
        wlib.headers[name] = value
    else:
        # normal the loop should break when first blank line seen.
        # this file is either empty or has no body part.
        # treat this as empty wlib.
        return wlib

    lineno += 1     # adjust lineno to next line the reader is going to return
    lineno += 1     # make it one based
    for lineno, row in dsv.parse(reader, lineno):
        try:
            parseLine(wlib, row)
        except KeyError, e:
            log.warn('KeyError line %s: %s', lineno, e)
        except ValueError, e:
            log.warn('ValueError line %s: %s', lineno, e)
        except Exception, e:
            log.warn('Parsing error line %s: %s', lineno, e)
            raise

    # completed reading all tags and webpages, convert tagIds to tag
    for item in wlib.webpages:
        tags = [wlib.tags.getById(id) for id in item.tagIds]
        item.tags = filter(None, tags)
        # remove tagIds to avoid duplicated data?

    wlib.category.compile()
    return wlib


def parseLine(wlib, row):
    """ raise ValueError or KeyError for parsing problem """
    # TODO: field validation
    if row.id[0:1] == '@':
        tag_id = row.id[1:]
        tag = weblib.Tag(
            id   = int(tag_id),
            name = row.name,
        )
        wlib.addTag(tag)

    else:
        if row.tagids:
            s = row.tagids.replace('@','')
            tagIds = [int(id) for id in s.split(',')]
        else:
            tagIds = []

        entry = weblib.WebPage(
            id          = int(row.id),
            name        = row.name,
            description = row.description,
            tagIds      = tagIds,
            flags       = row.flags,
            modified    = row.modified,
            lastused    = row.lastused,
            cached      = row.cached,
            archived    = row.archived,
            url         = row.url,
        )
        wlib.addWebPage(entry)



def parseFields(line):
    ### TODO: should use header line to maintain compatability
    data = dsv.parse(line)

    if len(data) < NUM_COLUMN:
        return data + [None] * (NUM_COLUMN - len(data))
    else:
        return data[:NUM_COLUMN]



def save(wstream, wlib):
    writer = codecs.getwriter('utf8')(wstream,'replace')

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

    # output tags
    for item in wlib.tags:
        id = '@%d' % item.id
        data = dsv.encode_fields([id, item.name] + [''] * (NUM_COLUMN-2))
        writer.write(data)
        writer.write('\n')

    # output webpages
    for item in wlib.webpages:
        id = str(item.id)
        tagIds = ','.join(['@%s' % t.id for t in item.tags])
        data = dsv.encode_fields([
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
        writer.write(data)
        writer.write('\n')


# ------------------------------------------------------------------------
# command line testing

def main(argv):
    if len(argv) < 2:
        print __doc__
        sys.exit(-1)

    # load
    fp = file(argv[1],'rb')
    wlib = load(fp)
    fp.close()

    print 'Loaded %s\ncategory_description:\n%s\n#tags %s\n#webpages %s' % (
        argv[1], wlib.headers['category_description'].encode('raw_unicode_escape'), len(wlib.tags), len(wlib.webpages))

    # save
    if len(argv) > 2:
        fp = file(argv[2],'wb')
        save(fp, wlib)
        fp.close()


if __name__ == '__main__':
    main(sys.argv)