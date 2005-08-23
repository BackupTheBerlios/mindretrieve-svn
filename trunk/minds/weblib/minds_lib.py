"""Usage: minds_lib.py input_file output_file
"""

import codecs
import logging
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
'relatedIds',   # 04
'modified',     # 05
'lastused',     # 06
'cached',       # 07
'archived',     # 08
'flags',        # 09
'url',          # 10
]

NUM_COLUMN = len(COLUMNS)


def load(rstream):
    wlib = weblib.WebLibrary()
    for lineno, row in dsv.parse(rstream):
        try:
            parseLine(wlib, row)
        except KeyError, e:
            log.warn('line %s - %s', lineno, e)
        except ValueError, e:
            log.warn('line %s - %s', lineno, e)
    wlib.fix()
    return wlib


def parseLine(wlib, row):
    """ raise ValueError or KeyError for parsing problem """

    # TODO: field validation

    if row.id[0:1] == '+':
        tag = weblib.Tag(
            id          = int(row.id[1:]),
            name        = row.name,
        )
        wlib.addTag(tag)

    else:
        if row.tagids:
            tagIds = [int(id) for id in row.tagids.split(',')]
        else:
            tagIds = []
            
        if row.relatedids:
            relatedIds = [int(id) for id in row.relatedids.split(',')]
        else:
            relatedIds = []

        entry = weblib.WebPage(
            id          = int(row.id),
            name        = row.name,
            description = row.description,
            tagIds    = tagIds,
            relatedIds  = relatedIds,
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

    writer.write('#encoding=UTF8\n')
    writer.write('#version=0.5\n')
    header = dsv.encode_fields(COLUMNS)
    writer.write(header)
    writer.write('\n')

    for item in wlib.tags:

        id = '+%d' % item.id

        data = dsv.encode_fields([id, item.name] + [''] * (NUM_COLUMN-2))

        writer.write(data)
        writer.write('\n')


    for item in wlib.webpages:

        id = str(item.id)
        tagIds = [str(t.id) for t in item.tags]
        tagIds = ','.join(tagIds)
        relatedIds = ''##

        data = dsv.encode_fields([
            id              ,
            item.name       ,
            item.description,
#            item.comment    ,
            tagIds        ,
            relatedIds      ,
            item.modified   ,
            item.lastused   ,
            item.cached     ,
            item.archived   ,
            item.flags      ,
            item.url        ,
            ])
        writer.write(data)
        writer.write('\n')




def main(argv):

    if len(argv) < 2:
        print __doc__
        sys.exit(-1)

    # load
    fp = file(argv[1],'rb')
    wlib = load(fp)
    fp.close()

    # save
    if len(argv) > 2:
        fp = file(argv[2],'wb')
        save(fp, wlib)
        fp.close()


if __name__ == '__main__':
    main(sys.argv)