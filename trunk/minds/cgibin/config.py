import cgi
import datetime
import logging
import os, sys

from minds import qmsg_processor
import configTmpl

log = logging.getLogger('cgi.config')


def showHome(wfile, env):
    wfile.write(
"""Content-type: text/html\r
Cache-control: no-cache\r
\r
"""
)
    numIndexed, numQueued = qmsg_processor.getQueueStatus()
    d = datetime.datetime.now()

    from minds import app_httpserver
    app_httpserver.forwardTmpl(wfile, env, 'config.html',
        configTmpl,
        numIndexed, numQueued,
        str(d))


def reload(wfile, env):
    modules = [m for m in sys.modules if m.startswith('minds.')]
    for m in modules:
        if m != 'minds.config' and sys.modules[m] != None:
            log.info('Reloading modules: #%s', m)
            del sys.modules[m]
    log.info('Reloading modules: #%d', len(modules))

    showHome(wfile, env)


def indexNow(wfile, env):
    pass


def shutdown(wfile, env):
    log.info('Begin system shutdown!')

    wfile.write(
"""Content-type: text/html\r
Cache-control: no-cache\r
\r
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3c.org/TR/html4/loose.dtd">
<html>
<head>
<title>Shutdown</title>
</head>
<body>
<pre>
%s: System shutting down. Goodbye.
</pre>
</body>
</html>

""" % str(datetime.datetime.now())
)
    from minds import proxy
    proxy.shutdown()



def main(rfile, wfile, env):

    form = cgi.FieldStorage(fp=rfile, environ=env)

    action = form.getfirst('action', '')

    if not action:
        showHome(wfile, env)

    elif action == 'indexnow':
        indexNow(wfile, env)

    elif action == 'shutdown':
        shutdown(wfile, env)

    else:
        log.warn('Unknown action: %s', action)
        showHome(wfile, env)

if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)