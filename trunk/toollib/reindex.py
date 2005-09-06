"""Usage: reindex.py index_dir
"""

import datetime
import shutil
import StringIO
import sys

from minds.config import cfg
from minds import distillparse
from minds import docarchive
from minds import lucene_logic


NOTIFY_INTERVAL = 100

def reindex(dbdoc, beginId, endId, index_path):

    ah = docarchive.ArchiveHandler('r')

    writer = lucene_logic.Writer(index_path)
    writer.writer.minMergeDocs = 1000

    for i in xrange(beginId, endId):

        docid = '%09d' % i
        if i % NOTIFY_INTERVAL == 1:
            print '%s Reindexing %09d' % (datetime.datetime.now(), i)

        zfile, filename = ah._open(docid)
        try:
            data = zfile.read(filename)
        except KeyError:
            continue        # skip holes

        fp = StringIO.StringIO(data)
        meta, content = distillparse.parseDistillML(fp, distillparse.writeHeader)
        writer.addDocument(docid, meta, content)

    print '%s optimizing' % datetime.datetime.now()
    writer.optimize()
    writer.close()

    ah.close()


def main(argv):

    if len(argv) < 2:
        print __doc__
        sys.exit(-1)

    index_path = argv[1]
    shutil.rmtree(index_path, True)

    starttime = datetime.datetime.now()
    dbdoc = cfg.getPath('archive')
    idc = docarchive.idCounter
    idc._findIdRange()
    beginId = idc._beginId
    endId   = idc._endId
    print 'Reindex %s(#%d-%d) -> %s' % (dbdoc, beginId, endId, index_path)
    reindex(dbdoc, beginId, endId, index_path)
    print 'Reindex finished:', datetime.datetime.now() - starttime


if __name__ == '__main__':
    main(sys.argv)
