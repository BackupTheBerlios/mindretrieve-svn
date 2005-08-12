#!/usr/bin/python
"""Usage: runcgi <relative URI>

Helper to test CGI via app_httpserver

1. Run minds.app_httpserver <relative URI>
2. fix link: href="/main.css" -> href="htdocs/main.css"
3. save to 1.html
4. Open 1.html with browser

Note: output is buffered in memory before writing to 1.html

"""

import sys
import StringIO
import webbrowser

from minds import app_httpserver
from minds.util import fileutil


def fix_link(rfile,wfile):
   for line in rfile:
        line = line.replace('href="/main.css"', 'href="lib/htdocs/main.css"')
        wfile.write(line)


def main():

    from minds import proxy
    proxy.init(proxy.CONFIG_FILENAME)

    buf = fileutil.aStringIO()
    sys.stdout = buf
    try:
        app_httpserver.main()
    finally:
        sys.stdout = sys.__stdout__

    buf.seek(0)
    fp = file('1.html','wb')
    fix_link(buf,fp)
    fp.close()

    print 'See output in 1.html'

    # what's wrong with opera?
    webbrowser.open("1.html")


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print __doc__
        sys.exit(-1)

    if sys.platform == "win32":
        import msvcrt,os
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    main()