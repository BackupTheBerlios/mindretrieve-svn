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

(
ID         ,    # 0
NAME       ,    # 1
DESCRIPTION,    # 2
COMMENT    ,    # 3
LABELIDS   ,    # 4
FLAGS      ,    # 5
CREATED    ,    # 6
MODIFIED   ,    # 7
ARCHIVED   ,    # 8
URL        ,    # 9
) = range(NUM_COLUMN)



def scanLine(reader):
    for lineno, line in enumerate(reader):
        line = line.rstrip()
        if line and not line.startswith('#'):
            yield lineno, line


def load(rstream):

    reader = codecs.getreader('utf8')(rstream,'replace')
    lineScanner = scanLine(reader)

    wlib = weblib.WebLibrary()

    lineno, header = lineScanner.next()

    for lineno, line in lineScanner:
        try:
            parseLine(wlib, line)
        except KeyError, e:
            log.warn('line %s - %s', lineno+1, e)
        except ValueError, e:
            log.warn('line %s - %s', lineno+1, e)

    for item in wlib.webpages:
        weblib.setTags(item, wlib)

    for item in wlib.labels:
        weblib.inferRelation(item)

    return wlib



def parseLine(wlib, line):
    """ raise ValueError or KeyError for parsing problem """

    data = parseFields(line)

    # TODO: field validation

    if data[ID][0:1] == '+':
        label = weblib.Label(
            id          = int(data[ID][1:]),
            name        = data[NAME],
        )
        wlib.addLabel(label)

    else:
        labelIds = []
        _labelIds = data[LABELIDS].strip()
        if _labelIds:
            labelIds = [int(id) for id in _labelIds.split(',')]

        entry = weblib.WebPage(
            id          = int(data[ID]),
            name        = data[NAME         ],
            description = data[DESCRIPTION  ],
            comment     = data[COMMENT      ],
            labelIds    = labelIds           ,
            flags       = data[FLAGS        ],
            created     = data[CREATED      ],
            modified    = data[MODIFIED     ],
            archived    = data[ARCHIVED     ],
            url         = data[URL          ],
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
    header = dsv.encode(COLUMNS)
    writer.write(header)
    writer.write('\n')

    for item in wlib.labels:

        id = '+%d' % item.id

        data = dsv.encode([id, item.name] + [''] * (NUM_COLUMN-2))

        writer.write(data)
        writer.write('\n')


    for item in wlib.webpages:

        id = str(item.id)
        labelIds = ','.join(map(str,item.labelIds))

        data = dsv.encode([
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