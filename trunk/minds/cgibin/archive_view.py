import cgi
import codecs
import logging
import sys

from minds.config import cfg
from minds import distillparse
from minds import docarchive

log = logging.getLogger('cgi.archive_view')


def main(rfile, wfile, env):

    form = cgi.FieldStorage(fp=rfile, environ=env)

    docid = form.getvalue('docid','')
    if len(docid) != 9:
        pass                                            # todo: 404

    wfile.write(
"""Content-type: text/html; charset=UTF-8\r
Cache-control: no-cache\r
\r
""")

    fp = docarchive.get_document(docid)
    distillparse.render(fp, wfile)                  # todo: except 404
#        d1 = '%09d' % (int(docid) + 1,)
#        n = '/archive_view?docid=%s' % d1
#        distillparse._render(fp, wfile, n)         # todo: except 404


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)