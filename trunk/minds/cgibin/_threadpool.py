import cgi
import datetime
import logging
import os, sys

log = logging.getLogger('cgi.config')


def main(rfile, wfile, env):

    form = cgi.FieldStorage(fp=rfile, environ=env)

    wfile.write(
"""Content-type: text/plain\r
Cache-control: no-cache\r
\r
""")

    from minds import proxy

    msg = []
    now = datetime.datetime.now()
    for i, obj in enumerate(proxy.proxy_httpd.worker_status):
        if not obj:
            msg.append('%02d Idle' % i)
            continue
        duration = now - obj.starttime
        msg.append('%02d %s - %s' % (i, duration, obj.path))
    print >>wfile, '\n'.join(msg)
    #print >>wfile, proxy.proxy_httpd.showStatus()


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)