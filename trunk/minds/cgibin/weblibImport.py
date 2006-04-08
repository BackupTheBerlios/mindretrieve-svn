import logging
import os
import StringIO
import sys
import urllib2
from xml import sax
from xml.sax import saxutils

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
        doShowForm(wfile,req)


def doShowForm(wfile,req):
    renderer = ImportRenderer(wfile)
    renderer.setLayoutParam('MindRetrieve - Import')
    renderer.output()


def doDeli(wfile,req):
    fp = None
    error_title = ''
    errors = []
    added = None
    updated = None

    if not DEBUG:
        url = req.param('url')
        assert url
        username = req.param('username')
        password = req.param('password')
        errors = [
            'URL: %s' % url,
            'username: %s' % username,
            'password: ***',
        ]
        try:
            fp = import_delicious.fetch_delicious(url, username, password)
        except urllib2.HTTPError, e:
            if e.code == 401:       # 401: Authorization Required?
                error_title = 'Authorization Error'
            else:
                error_title = str(e)
        except IOError, e:
            log.exception('import_delicious.fetch_delicious error: %s:%s' % (username,'***'))
            error_title = str(e)

    else:
        fp = _openDeliTestDocument()

    if fp:
        added, updated = import_delicious.import_bookmark(fp)
        # note: import_bookmark() would capture sax.SAXParseException

    renderer = ImportStatusRenderer(wfile)
    renderer.setLayoutParam('MindRetrieve - Import')
    renderer.output(error_title, errors, added, updated, None)


def doMoz(wfile,req):
    error_title = ''
    added = None
    updated = None

    file_field = req.form['file']
    fp = StringIO.StringIO(file_field.value)

    # sanity check first
    if file_field.value.find('NETSCAPE-Bookmark-file',0,256) >= 0:
        added, updated = import_netscape.import_bookmark(fp)
    else:
        log.warn('Incorrect netscape bookmark format: %s' % file_field.value[:50].encode('string_escape'))
        error_title = 'Error: incorrect bookmark file format'

    renderer = ImportStatusRenderer(wfile)
    renderer.setLayoutParam('MindRetrieve - Import')
    renderer.output(error_title, [], added, updated, None)


def doOpera(wfile,req):
    error_title = ''
    added = None
    updated = None

    file_field = req.form['file']
    fp = StringIO.StringIO(file_field.value)

    # sanity check first
    if file_field.value.find('Opera',0,100) >= 0:
        added, updated = import_opera.import_bookmark(fp)
    else:
        log.warn('Incorrect opera bookmark format: %s' % file_field.value[:50].encode('string_escape'))
        error_title = 'Error: incorrect bookmark file format'

    renderer = ImportStatusRenderer(wfile)
    renderer.setLayoutParam('MindRetrieve - Import')
    renderer.output(error_title, [], added, updated, None)


# ----------------------------------------------------------------------

class ImportRenderer(response.WeblibLayoutRenderer):

    TEMPLATE_FILE = 'weblibImport.html'

    def render(self, node):
        node.url.atts['value'] = import_delicious.POSTS_URL
        node.view_url.atts['value'] = import_delicious.POSTS_URL


class ImportStatusRenderer(response.WeblibLayoutRenderer):

    TEMPLATE_FILE = 'weblibImportStatus.html'

    def render(self, node, error_title, errors, added, updated, skipped):
        if error_title:
            node.status.omit()
            node.error_msg.header.content = error_title
            escaped_errors = map(saxutils.escape, errors)
            node.error_msg.detail.raw = '<br />'.join(escaped_errors)

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