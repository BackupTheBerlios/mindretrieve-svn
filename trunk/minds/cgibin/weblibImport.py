import logging
import os
import sys
import urllib2

from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response

from minds.weblib import import_delicious
from minds.weblib import import_netscape
from minds.weblib import import_opera


log = logging.getLogger('cgi.wlibImp')

DEBUG = 0

def _openDeliTestDocument(): return file('g:\\bin\\py_repos\\mindretrieve\\trunk\\lib\\testdocs\\bookmark\\delicious.xml','rb')


def main(rfile, wfile, env):
    req = request.Request(rfile, env)
    path = env.get('PATH_INFO', '')
    if path == '/deli':
        doDeli(wfile, req)
    elif path == '/ie':
        doIE(wfile, req)
    elif path == '/moz':
        doMoz(wfile, req)
    elif path == '/opera':
        doOpera(wfile, req)
    elif path == '/safari':
        doSafari(wfile, req)
    else:
        doShowForm(wfile)


def doShowForm(wfile):
    ImportRenderer(wfile).output()


def doDeli(wfile,req):
    fp = None
    error_msg = ''
    added = None
    updated = None

    if not DEBUG:
        username = req.param('username')
        password = req.param('password')
        try:
            fp = import_delicious.fetch_delicious(
                import_delicious.POSTS_URL,
                username,
                password,
                )
        except urllib2.HTTPError, e:
            # 401: Authorization Required?
            if e.code == 401:
                error_msg = '401'
            else:
                error_msg = str(e)
        except IOError, e:
            log.exception('import_delicious.fetch_delicious error: %s:%s' % (username,'***'))
            error_msg = str(e)
    else:
        fp = _openDeliTestDocument()

    if fp:
        added, updated = import_delicious.import_bookmark(fp)

    ImportStatusRenderer(wfile)\
        .output(error_msg, added, updated, None)



# ----------------------------------------------------------------------

class ImportRenderer(response.WeblibLayoutRenderer):

    TEMPLATE_FILE = 'weblibImport.html'

    def render(self, node):
        node.view_url.atts['value'] = import_delicious.POSTS_URL


class ImportStatusRenderer(response.WeblibLayoutRenderer):

    TEMPLATE_FILE = 'weblibImportStatus.html'

    def render(self, node, error_msg, added, updated, skipped):
        if error_msg:
            node.status.omit()
            if error_msg == '401':
                pass # canned error
            else:
                node.error_msg.message.content = error_msg
            node.error_msg.view_url.content = import_delicious.POSTS_URL

        else:
            node.error_msg.omit()
            if added is None:
                node.status.added.omit()
            else:
                node.status.added.content %= added
            if updated is None:
                node.status.updated.omit()
            else:
                node.status.updated.content %= updated
            if skipped is None:
                node.status.skipped.omit()
            else:
                node.status.skipped.content %= skipped


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)