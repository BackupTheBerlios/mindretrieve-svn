import datetime
import logging
import os
import sys

from minds.config import cfg
from minds.cgibin.util import request


log = logging.getLogger('cgi.cntrol')

def main(rfile, wfile, env):
    req = request.Request(rfile, env)
    path = env.get('PATH_INFO', '')
    if path == '/config':
        doConfig(wfile,req)
    elif path == '/reload':
        doReload(wfile)
    elif path == '/shutdown':
        doShutdown(wfile)
    else:
        showStatus(wfile)



def showStatus(wfile):
    wfile.write(
"""Content-type: text/html\r
Cache-control: no-cache\r
\r
""")

    now = datetime.datetime.now()
    print >>wfile, '<pre>'
    print >>wfile, 'Date: %s' % str(now)[:19],
#    print >>wfile, '<a href="/___/reload">Reload</a>',
    print >>wfile, '<a href="/___/shutdown">Shutdown</a>'

    # show thread status
    print >>wfile, '\n------------------------------------------------------------------------'
    print >>wfile, 'proxy_httpd.worker_status\n'
    from minds import proxy
    if proxy.proxy_httpd:
        msg = []
        for i, obj in enumerate(proxy.proxy_httpd.worker_status):
            if not obj:
                msg.append('%02d Idle' % i)
                continue
            duration = now - obj.starttime
            msg.append('%02d %s - %s' % (i, duration, obj.path))
        print >>wfile, '\n'.join(msg)
    else:
        print >>wfile, 'proxy.proxy_httpd not defined'

    # show config
    print >>wfile, '\n------------------------------------------------------------------------'
    print >>wfile, 'Config'
    print >>wfile, '<form action="/___/config" method="GET">'
    print >>wfile, 'Key <input type="text" name="key" value="messagelog.mlog"/>',
    print >>wfile, 'Value <input type="text" name="value" />',
    print >>wfile, '<input type="submit" />',
    print >>wfile, '</form>'
    print >>wfile, str(cfg)



def doConfig(wfile,req):
    key = req.param('key')
    value = req.param('value')
    if key:
        log.debug('Config set [%s]="%s"' % (key,value))
        cfg.set(key, value)
    showStatus(wfile)



# 2006-01-14 Reload does not seem to work
# Got this error:
#   AttributeError: 'NoneType' object has no attribute 'worker_status'
# Impossible to reload proxy?
def doReload(wfile):
    for m in sorted(sys.modules.keys()):
        if not m.startswith('minds.'):
            continue
        if m == __name__:
            continue
        log.info('Reloading modules: %s', m)
        del sys.modules[m]
    showStatus(wfile)



def doShutdown(wfile):
    wfile.write(
"""Content-type: text/plain\r
Cache-control: no-cache\r
\r
%s: System shutting down. Goodbye.
""" % str(datetime.datetime.now())
)
    from minds import proxy
    proxy.shutdown()



if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)