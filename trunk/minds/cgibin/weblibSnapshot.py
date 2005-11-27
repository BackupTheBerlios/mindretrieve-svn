import cgi
import datetime
import logging
import os
import string
import sys

from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import mhtml
from minds.weblib import snapshot
from minds.weblib import store

log = logging.getLogger('cgi.snapsh')

# Handles these URI
#   /weblib/$rid/snapshotFrame
#   /weblib/$rid/snapshotHeader
#   /weblib/$rid/snapshot
#   /weblib/$rid/snapshot/get       <---- TODO make this more REST?

def main(wfile, env, method, form, rid, rid_path):
    wlib = store.getWeblib()
    item = wlib.webpages.getById(rid)

    str_rid = rid == -1 and '_' or str(rid)

    if rid_path == 'snapshotFrame':
        FrameRenderer(wfile).output(str_rid, item and item.name or '')
    elif rid_path == 'snapshotHeader':
        if item:
            HeaderRenderer(wfile).output(item.name, item.cached, item.url)
        else:
            HeaderRenderer(wfile).output('?', '?', '?')
    elif rid_path == 'snapshot':
        doShowSnapshot(wfile, rid, rid_path)
    elif rid_path == 'snapshot/get':
        doSnapshot(wfile, form, str_rid, item)
        wlib.updateWebPage(item)
    else:
        wfile.write('404 not found\r\n\r\n%s not found' % rid)


def doShowSnapshot(wfile, rid, rid_path):
    # the rid_path are really for user's information only.
    # rid alone determines where to go.
    wlib = store.getWeblib()
    item = wlib.webpages.getById(rid)
    if not item:
        wfile.write('404 not found\r\n\r\n%s not found' % rid)
        return

    filename = rid == -1 and '_.mhtml' or '%s.mhtml' % rid
    # TODO: check file exist, move to weblib? getSnapshotFile()?
    fp = (cfg.getpath('weblibsnapshot')/filename).open('rb')

    obj = mhtml.LoadedWebArchive.load_fp(fp)
    # do visit?
    # wlib.visit(item)
    response.redirect(wfile, obj.root_uri)


def doSnapshot(wfile, form, str_rid, item):
    url = form.getfirst('url')
    if not url and item:
        url = item.url
    shot = snapshot.Snapshot()
    shot.fetch(url)
    spath = cfg.getpath('weblibsnapshot')/('%s.mhtml' % str_rid)
    fp = spath.open('wb')
    try:
        shot.generate(fp)
    finally:
        fp.close()
    if item:
        t = datetime.datetime.now()
        item.cached = str(t)[:10]

    response.redirect(wfile, '../snapshotFrame')



# ----------------------------------------------------------------------

class FrameRenderer(response.CGIRenderer):
    TEMPLATE_FILE = 'snapshotFrame.html'
    """ 2005-09-14
    con:title
    con:header
    con:body
    """
    def render(self, node, str_rid, title):
        node.title.content = title
        hsrc = node.header.atts['src']
        node.header.atts['src'] = string.Template(hsrc).safe_substitute(rid=str_rid)
        hsrc = node.body.atts['src']
        node.body.atts['src'] = string.Template(hsrc).safe_substitute(rid=str_rid)  # TODO: actually we can get rid of str_rid by using relative url


class HeaderRenderer(response.CGIRenderer):
    TEMPLATE_FILE = 'snapshotHeader.html'
    """ 2005-09-14
    con:heading
    """
    def render(self, node, name, date, url):
        node.heading.content = '[%s] %s - %s' % (
            str(date)[:10],
            name,
            len(url) > 50 and url[:50]+'...' or url,
            )

# weblibForm get invoked from CGI weblib.py

#if __name__ == "__main__":
#    main(sys.stdin, sys.stdout, os.environ)
