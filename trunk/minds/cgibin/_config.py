import cgi
import datetime
import logging
import os, sys

from minds.config import cfg

log = logging.getLogger('cgi.config')


def main(rfile, wfile, env):

    from minds import proxy
    cfg.load(proxy.CONFIG_FILENAME)

    form = cgi.FieldStorage(fp=rfile, environ=env)

    mlog = form.getfirst('mlog', '')
    cfg.set('messagelog','mlog',mlog)

    wfile.write(
"""Content-type: text/plain\r
Cache-control: no-cache\r
\r
""")
    cfg.dump(wfile)


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)