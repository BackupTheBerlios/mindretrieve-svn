#!/usr/bin/python
import cgi
import os, sys
import shutil

#import cgitb; cgitb.enable()

ENV = [
'AUTH_TYPE',
'CONTENT_LENGTH',
'CONTENT_TYPE',
'GATEWAY_INTERFACE',
'PATH_INFO',
'PATH_TRANSLATED',
'QUERY_STRING',
'REMOTE_ADDR',
'REMOTE_HOST',
'REMOTE_IDENT',
'REMOTE_USER',
'REQUEST_METHOD',
'SCRIPT_NAME',
'SERVER_NAME',
'SERVER_PORT',
'SERVER_PROTOCOL',
'SERVER_SOFTWARE',
]

def main(rfile, wfile, env):

    form = cgi.FieldStorage(fp=rfile, environ=env, keep_blank_values=1)

    print >>wfile, "Content-type: text/html\r"
    print >>wfile, """\r
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3c.org/TR/html4/loose.dtd">
<html>
<head>
<title>Snoop</title>
<http-equiv="Content-Type" content="text/html; charset=iso-8859-1">
<style>
  body  { font-family: sans-serif; font-size: 80% }
  table { font-size: 100% }    /* hack? without this table cells won't inherit body's font-size */
  th    { text-align: left }
</style>
</head>

<body>
<h1>Snoop</h1>
"""

    print >>wfile, \
"""
<h3>Query String</h3>
<table border='1' cellspacing='0'>
  <tr><th>Name</th><th>Value</th></tr>
"""
    keys = form.keys()
    keys.sort()
    for k in form.keys():
        val = form.getvalue(k)
        print >>wfile, "  <tr><td>%s</td><td>%s</td></tr>" % (cgi.escape(k), cgi.escape(str(val)))
    print >>wfile, "</table>"


    print >>wfile, \
"""
<h3>Environ</h3>
<table border='1' cellspacing='0'>
<tr><th>Name</th><th>Value</th></tr>
"""
    keys = env.keys()
    keys.sort()
    cgikeys = []
    otherkeys = []
    for k in keys:
        kl = k.upper()
        if kl in ENV or kl.startswith('HTTP_'):
            cgikeys.append(k)
        else:
            otherkeys.append(k)
    for k in cgikeys:
        val = cgi.escape(env[k]) or '&nbsp;'
        print >>wfile, "<tr><td>%s</td><td>%s</td></tr>" % (cgi.escape(k), val)
    print >>wfile, "</table>"


    # do this only after checking content-length?
# below hang up when no input???
#    print >>wfile, "<h3>Input</h3>"
#    print >>wfile, "<pre>"
#    shutil.copyfileobj(rfile, wfile)
#    print >>wfile, "</pre>"

    print >>wfile, \
"""
</body>
</html>
"""


if __name__ == '__main__':
    main(sys.stdin, sys.stdout, os.environ)