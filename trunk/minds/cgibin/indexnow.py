import cgi
import os, sys

from minds import qmsg_processor
import templateTmpl


def main(rfile, wfile, env):

    form = cgi.FieldStorage(fp=rfile, environ=env)

    transformed, indexed, discarded = qmsg_processor.backgroundIndexTask(forceIndex=True)
    msg = 'Indexed %s discarded %s' % (indexed, discarded)

    wfile.write(
"""Content-type: text/html\r
Cache-control: no-cache\r
\r
""")
    from minds import app_httpserver
    app_httpserver.forwardTmpl(wfile, env, 'template.html', templateTmpl, msg)


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)