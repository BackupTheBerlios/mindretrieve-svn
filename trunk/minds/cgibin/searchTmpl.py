"""
"""

from minds.util import httputil

BASE_URI = 'search?'

def trim(s, maxlen):
    if len(s) <= maxlen: return s
    return s[:maxlen] + '...'


def render(node, qform, page, title, query, error_msg, matchList):
    node.title.content = title
    node.query.atts['value'] = query

    node.match_item.repeat(renderMatchItem, matchList)

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

        nav.goto_page.repeat(renderGotoPage, xrange(page.page_window_start, page.page_window_end),
            qform, page.page, page.page_size)



def renderGotoPage(node, goto_page, qform, curPage, page_size):
    if goto_page == curPage:
        del node.atts['href']
        node.content = '[%s]' % (goto_page+1)
    else:
        node.atts['href'] = qform.makeQueryString(start=goto_page*page_size)
        node.content = str(goto_page+1)



def renderMatchItem(node, match):
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



###testing#########

class Bag:
    pass

from toollib.HTMLTemplate import *

def main():
    template = Template(render, file("search.html").read())
    o1 = Bag()
    o1.docid        = '_'
    o1.title        = 'aTitle'
    o1.description  = 'aDesc'
    o1.uri          = 'abc'
    o1.score        = 1
    o2 = Bag()
    o2.docid        = '_'
    o2.title        = ''
    o2.description  = ''
    o2.uri          = 'def'
    o2.score        = 0
    print template.render('hello',10,[o1,o2])

if __name__ == '__main__':
    main()