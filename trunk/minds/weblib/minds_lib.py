"""Usage: minds_bm.py input_file output_file
"""

import codecs
import logging
import sys

from minds.config import cfg
from minds import weblib
from minds.util import dsv



log = logging.getLogger('wlib.minds')


COLUMNS = [
'id',           # 0
'name',         # 1
'description',  # 2
'comment',      # 3
'labelIds',     # 4
'flags',        # 5
'created',      # 6
'modified',     # 7
'archived',     # 8
'url',          # 9
]

NUM_COLUMN = len(COLUMNS)

#(
#ID         ,    # 0
#NAME       ,    # 1
#DESCRIPTION,    # 2
#COMMENT    ,    # 3
#LABELIDS   ,    # 4
#FLAGS      ,    # 5
#CREATED    ,    # 6
#MODIFIED   ,    # 7
#ARCHIVED   ,    # 8
#URL        ,    # 9
#) = range(NUM_COLUMN)



def load(rstream):

    wlib = weblib.WebLibrary()

    ###lineno, header = lineScanner.next()

    for lineno, row in dsv.parse(rstream):
        try:
            parseLine(wlib, row)
        except KeyError, e:
            log.warn('line %s - %s', lineno, e)
        except ValueError, e:
            log.warn('line %s - %s', lineno, e)

    for item in wlib.webpages:
        weblib.setTags(item, wlib)

    for item in wlib.labels:
        weblib.inferRelation(item)

    return wlib



def parseLine(wlib, row):
    """ raise ValueError or KeyError for parsing problem """

    # TODO: field validation

    if row.id[0:1] == '+':
        label = weblib.Label(
            id          = int(row.id[1:]),
            name        = row.name,
        )
        wlib.addLabel(label)

    else:
        if row.labelids:
            labelIds = [int(id) for id in row.labelids.split(',')]
        else:
            labelIds = []

        entry = weblib.WebPage(
            id          = int(row.id),
            name        = row.name,
            description = row.description,
            comment     = row.comment,
            labelIds    = labelIds,
            flags       = row.flags,
            created     = row.created,
            modified    = row.modified,
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

    for item in wlib.labels:

        id = '+%d' % item.id

        data = dsv.encode_fields([id, item.name] + [''] * (NUM_COLUMN-2))

        writer.write(data)
        writer.write('\n')


    for item in wlib.webpages:

        id = str(item.id)
        labelIds = ','.join(map(str,item.labelIds))

        data = dsv.encode_fields([
            id              ,
            item.name       ,
            item.description,
            item.comment    ,
            labelIds        ,
            item.flags      ,
            item.created    ,
            item.modified   ,
#            item.archived   ,  ###TODO: clean up
            ''              ,
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