"""Usage: reindex.py index_dir
"""

import datetime
import shutil
import sys

from minds.config import cfg
from minds import distillparse
from minds import docarchive
from minds import lucene_logic


NOTIFY_INTERVAL = 100

def reindex(dbdoc, highestId, index_path):

    writer = lucene_logic.Writer(index_path)
    writer.writer.minMergeDocs = 1000

    zfp = None
    for i in xrange(1, highestId+1):
        docid = '%09d' % i
        if i % NOTIFY_INTERVAL == 1:
            print '%s Reindexing %09d' % (datetime.datetime.now(), i)
        zfp = docarchive.docarc.get_archive(docid, openedZipFile=zfp, closeIfNotNeeded=True)
        fp = docarchive.docarc.get_document(zfp, docid)
        meta, content = distillparse.parseDistillML(fp, distillparse.writeHeader)
        writer.addDocument(docid, meta, content)

    if zfp: zfp.close()

    print '%s optimizing' % datetime.datetime.now()
    writer.optimize()
    writer.close()



def main(argv):

    if len(argv) < 2:
        print __doc__
        sys.exit(-1)

    from minds import proxy
    proxy.init(proxy.CONFIG_FILENAME)

    index_path = argv[1]
    shutil.rmtree(index_path, True)

    dbdoc = cfg.getPath('archive')
    highestId = docarchive.docarc._findHighestId()
    print 'Reindex %s(#%d) -> %s' % (dbdoc, highestId, index_path)
    starttime = datetime.datetime.now()
    reindex(dbdoc, highestId, index_path)
    print 'Reindex finished:', datetime.datetime.now() - starttime


if __name__ == '__main__':
    main(sys.argv)
