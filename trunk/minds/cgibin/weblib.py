import cgi
import logging
import os, sys
import sets
import string
import urllib

from minds.config import cfg
from minds.cgibin import weblibSnapshot
from minds.cgibin import weblibForm
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import graph
from minds.weblib import store

log = logging.getLogger('cgi.weblib')


def main(rfile, wfile, env):
    method, form, rid, rid_path = request.parseURL(rfile, env)
    log.debug('method %s rid %s', method, rid)

    querytxt = form.getfirst('query','').decode('utf-8')
    tag = form.getfirst('tag','').decode('utf-8')

    wlib = store.getMainBm()
    if rid is None and (not form.has_key('tag')) and (not querytxt):
        # redirect to default tag (if it is defined)
        dt = wlib.getDefaultTag()
        if dt:
            url = request.tag_url([dt])
            response.redirect(wfile, url)
            return

    if form.getfirst('action') == 'cancel':
        response.redirect(wfile, request.WEBLIB_URL)

    elif rid_path and rid_path.startswith('go;'):
        doGoResource(wfile, rid, rid_path)

    elif rid and rid_path and rid_path.startswith('snapshot'):
        weblibSnapshot.main(rfile, wfile, env, method, form, rid, rid_path)

    elif querytxt:
        queryWebLib(wfile, env, form, tag, querytxt)

    elif rid is not None:
        weblibForm.main(rfile, wfile, env, method, form, rid)

    else:
        queryWebLib(wfile, env, form, tag, '')



def doGoResource(wfile, rid, rid_path):
    # the rid_path are really for user's information only.
    # rid alone determines where to go.
    wlib = store.getMainBm()
    item = wlib.webpages.getById(rid)
    if not item:
        wfile.write('404 not found\r\n\r\n%s not found' % rid)
        return

    wlib.visit(item)
    response.redirect(wfile, item.url)


def queryWebLib(wfile, env, form, tag, querytxt):
    go_direct = form.getfirst('submit') == '>'
    if querytxt.endswith('>'):
        querytxt = querytxt[:-1]
        go_direct = True

    wlib = store.getMainBm()
    if tag.startswith('@') and tag[1:].isdigit():
        id = int(tag[1:])
        tag = wlib.tags.getById(id)
        tags = tag and [tag] or []
    else:
        tags, _ = weblib.parseTags(wlib, tag)
    items, related, most_visited = weblib.query(wlib, querytxt, tags)
    if querytxt:
        tags_matched = weblib.query_tags(wlib, querytxt, tags)
        tags_matched = [t.name for t in tags_matched]
    else:
        tags_matched = ()

    ##related hack
    parents = []
    print >>sys.stderr, related
    if related and hasattr(related, '__len__'):
        parents = [t.tag for score,t in related[0]]
        related  = [t for score,t in related[0]] + ['c'] + \
            [t for score, t in related[1]] + ['r'] + \
            [t for score, t in related[2]]

    # quick jump?
    if go_direct and most_visited:
        wlib.visit(most_visited)
        response.redirect(wfile, most_visited.url)
        return

    folderNames = map(unicode, related)
    currentCategory = tags and unicode(tags[-1]) or ''
    categoryList = []
    top_nodes = wlib.categories[1]
    for node in top_nodes:
        subcat = []
        categoryList.append((unicode(node[0]), subcat))
        for v, path in graph.dfsp(node):
            if len(path) < 3:
                subcat.append(unicode(v))

    all_items = []
    for tags, lst in sorted(items.items()):
        tags = sets.Set(tags).difference(parents)
        for l in lst:
            all_items.append((l,tags))
            tags = ()
    WeblibRenderer(wfile, env, querytxt).output(most_visited, folderNames, categoryList, tags_matched, currentCategory, all_items)



# ----------------------------------------------------------------------

class WeblibRenderer(response.CGIRendererHeadnFoot):
    TEMPLATE_FILE = 'weblib.html'
    """ weblib.html
    con:header
    rep:catList
            con:link
            rep:catItem
                    con:link
    rep:crumb
            con:link
    con:go_hint
            con:address
    rep:webItem
            con:checkbox
            con:itemDescription
            con:itemTag
                    rep:tag
            con:edit
            con:delete
            con:cache
    con:footer
    """
    def render(self, node, most_visited, folderNames, categoryList, tags_matched, currentCategory, webItems):
        node.catList.repeat(self.renderCatItem, categoryList, currentCategory)

        if not webItems:
            node.web_items.omit()
            t = string.Template(node.no_match_msg.content)
            node.no_match_msg.content = t.safe_substitute(querytxt=self.querytxt)
            return

        node.no_match_msg.omit()

        if not most_visited:
            node.web_items.go_hint.omit()
        else:
            node.web_items.go_hint.address.atts['href'] = request.go_url(most_visited)
            node.web_items.go_hint.address.content = most_visited.name

        if not tags_matched:
            node.web_items.tags_matched.omit()
        else:
            node.web_items.tags_matched.tag.repeat(self.renderTagsmatched, tags_matched)

        node.web_items.crumb.repeat(self.renderCrumb, folderNames)
        node.web_items.webItem.repeat(self.renderWebItem, enumerate(webItems))

    def renderCrumb(self, node, item):
        node.link.content = item
        node.link.atts['href'] = request.tag_url(item)

    def renderTagsmatched(self, node, tag):
        node.content = tag
        node.atts['href'] = request.tag_url(tag)

    def renderCatItem(self, node, item, currentCategory):
        cat, subcat = item
        node.link.content = cat
        node.link.atts['href'] = request.tag_url(cat)
        if cat == currentCategory:
            node.link.atts['class'] = 'CategoryCurrentItem'
        node.catItem.repeat(self.renderSubCat, subcat, currentCategory)

    def renderSubCat(self, node, item, currentCategory):
        node.link.content = item
        node.link.atts['href'] = request.tag_url(item)
        if item == currentCategory:
            node.link.atts['class'] = 'CategoryCurrentItem'

    def renderWebItem(self, node, (i, item)):
        item, tags = item   ##todo
        if i % 2 == 1:
            node.atts['class'] = 'altrow'
        node.checkbox.atts['name'] = str(item.id)
        node.itemDescription.content = unicode(item)
        node.itemDescription.atts['href'] = request.go_url(item)
        node.itemTag.tag.repeat(self.renderWebItemTag, tags)
        node.edit.atts['href'] = '%s/%s/form' % (request.WEBLIB_URL, item.id)
        node.delete.atts['href'] = '%s/%s?method=delete' % (request.WEBLIB_URL, item.id)
        if item.cached:
            node.cache.atts['href'] = '%s/%s/snapshotFrame' % (request.WEBLIB_URL, item.id)
            node.cache.content = item.cached
        else:
            node.cache.atts['href'] = '%s/%s/snapshot/get' % (request.WEBLIB_URL, item.id)
            node.cache.content = 'download'

    def renderWebItemTag(self, node, tag):
        node.content = unicode(tag)
        node.atts['href'] = request.tag_url([tag])


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)