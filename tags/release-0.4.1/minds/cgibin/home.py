import cgi
import codecs
import os, sys

import homeTmpl

def main(rfile, wfile, env):

    form = cgi.FieldStorage(fp=rfile, environ=env)

    wfile.write(
"""Content-type: text/html; charset=utf-8\r
Cache-control: no-cache\r
\r
""")
    sw = codecs.getwriter('utf-8')(wfile,'replace')

    from minds import app_httpserver
    app_httpserver.forwardTmpl(wfile, env, 'home.html',
        homeTmpl)


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)