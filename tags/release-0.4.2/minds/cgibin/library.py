import cgi
import os, sys

import libraryTmpl


def main(rfile, wfile, env):

    form = cgi.FieldStorage(fp=rfile, environ=env)

    wfile.write(
"""Content-type: text/html\r
Cache-control: no-cache\r
\r
""")
    from minds import app_httpserver
    app_httpserver.forwardTmpl(wfile, env, 'library.html', libraryTmpl)


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)