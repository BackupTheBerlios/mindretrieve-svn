import cgi  ###TODO?
import logging
import os
import sys

from minds import qmsg_processor
from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds.util import httputil
from minds.util import pagemeter

log = logging.getLogger('cgi.histry')

PAGE_SIZE = 10


class QueryForm:
    def __init__(self, req):
        self.query = req.param('query')
        self.start = req.param('start')
        try:
            self.start = int(self.start)
        except:
            self.start = 0

    def makeQueryString(self, start=0):
        uri = '/history?query=%s&start=%s' % (
            cgi.escape(self.query),
            start,
            )
        return uri


def main(rfile, wfile, env):
    req = request.Request(rfile, env)
    qform = QueryForm(req)
    path = env.get('PATH_INFO', '')
    if path == '/indexnow':
        doIndexNow(wfile, req)
    elif qform.query:
        doSearch(wfile, req, qform)
    else:
        doGET(wfile, req, qform)


def doGET(wfile, req, qform):
    title = 'MindRetrieve - History'
    numIndexed, archive_date, numQueued = qmsg_processor.getQueueStatus()
    renderer = HistoryRenderer(wfile)
    renderer.setLayoutParam(title, '', response.buildBookmarklet(req.env))
    renderer.output(qform, numIndexed, archive_date, numQueued, None, qform.query, '', [])


def doIndexNow(wfile, req):
    transformed, indexed, discarded = qmsg_processor.backgroundIndexTask(forceIndex=True)
    response.redirect(wfile, '/history')


def doSearch(wfile, req, qform):
    from minds import search

    error_msg = ''
    num_match = 0
    matchList = []
    if qform.query:
        try:
            query = search.parseQuery(qform.query)
        except Exception, e:
            error_msg = e.args[0].split('\n')[0]
        else:
            num_match, matchList = search.search(query, qform.start, qform.start+PAGE_SIZE)

    page = pagemeter.PageMeter(qform.start, num_match, PAGE_SIZE)
    title = 'MindRetrieve - History: %s' % qform.query

    renderer = HistoryRenderer(wfile)
    renderer.setLayoutParam(title, '', response.buildBookmarklet(req.env))
    renderer.output(qform, 0, '', 0, page, qform.query, error_msg, matchList)


#------------------------------------------------------------------------

def trim(s, maxlen):
    if len(s) <= maxlen: return s
    return s[:maxlen] + '...'

BASE_URI = 'search?'

class HistoryRenderer(response.WeblibLayoutRenderer):

    TEMPLATE_FILE = 'history.html'
    """ 2006-01-13
    con:query
    con:indexStatus
            con:numIndexed
            con:numQueued
    con:search_result
            con:error_msg
            con:num_match
                    con:item_from
                    con:item_to
                    con:item_total
            rep:match_item
                    con:address
                    con:description
                    con:archive_link
                    con:host
            con:page_nav
                    con:goto_prev
                    rep:goto_page
                    con:goto_next
    """
    def render(self, node, qform, numIndexed, archive_date, numQueued, page, query, error_msg, matchList):
        node.query.atts['value'] = query

        if not query:
            node.search_result.omit()
            node.indexStatus.numIndexed.content = str(numIndexed)
            node.indexStatus.dateIndexed.content = archive_date[:10]
            if numQueued > 0:
                node.indexStatus.newDocuments.numQueued.content = str(numQueued)
            else:
                node.indexStatus.newDocuments.omit()
            return

        node.indexStatus.omit()

        ### TODO: clean up
        node = node.search_result

        node.match_item.repeat(self.renderMatchItem, matchList)

        if error_msg:
            node.num_match.omit()
            node.error_msg.content = error_msg
        else:
            node.error_msg.omit()
            node.num_match.item_from  .content = str(page.start+1)
            node.num_match.item_to    .content = str(page.end)
            node.num_match.item_total .content = str(page.total)

        # page control
        nav = node.page_nav
        if page.total_page == 1:
            nav.omit()                    # hide when there is only one page
        else:
            if page.prev is None:
                del nav.goto_prev.atts['href']
            else:
                nav.goto_prev.atts['href'] = qform.makeQueryString(start=page.prev)

            if page.next is None:
                del nav.goto_next.atts['href']
            else:
                nav.goto_next.atts['href'] = qform.makeQueryString(start=page.next)

            nav.goto_page.repeat(self.renderGotoPage, xrange(page.page_window_start, page.page_window_end),
                qform, page.page, page.page_size)



    def renderGotoPage(self, node, goto_page, qform, curPage, page_size):
        if goto_page == curPage:
            del node.atts['href']
            node.content = '[%s]' % (goto_page+1)
        else:
            node.atts['href'] = qform.makeQueryString(start=goto_page*page_size)
            node.content = str(goto_page+1)



    def renderMatchItem(self, node, match):
        uri = match.uri
        title = match.title and match.title or 'No title'
        scheme, userinfo, host, path, query, frag = httputil.urlsplit(uri)


        #import sys
        #print >>sys.stderr, type(title), title

        node.address.atts['href'] = uri
        node.address.content = title[:100]

        if match.description:
            node.description.raw = match.description
        else:
            node.description.omit()
        node.host.content = host

        # todo: hack
        node.archive_link.atts['href'] = '/archive_view?docid=%s' % str(match.docid)
        node.archive_link.content = match.date[:10]



if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)
