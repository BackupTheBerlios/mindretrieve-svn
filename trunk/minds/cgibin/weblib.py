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
    method, form, rid, tid, path = request.parse_weblib_url(rfile, env)
    log.debug('method %s rid %s', method, rid)

    wlib = store.getMainBm()

    if rid:
        # rid based (note rid maybe -1)
        if path and path.startswith('go;'):
            doGoResource(wfile, rid, path)
        elif path and path.startswith('snapshot'):
            weblibSnapshot.main(wfile, env, method, form, rid, path)
        elif path == 'form':
            weblibForm.main(wfile, env, method, form, rid)
        else:
            # show form by default
            weblibForm.main(wfile, env, method, form, rid)

    elif tid:
        doTag(wfile, env, method, form, tid)

    else:
        # query
        querytxt = form.getfirst('query','').decode('utf-8')
        tag = form.getfirst('tag','').decode('utf-8')

        # redirect to default tag (if it is defined)
        if (not 'tag' in form) and (not querytxt):
            dt = wlib.getDefaultTag()
            if dt:
                url = request.tag_url([dt])
                response.redirect(wfile, url)
                return

        if form.getfirst('action') == 'cancel':
            response.redirect(wfile, request.WEBLIB_URL)

        queryWebLib(wfile, env, form, tag, querytxt)


def doGoResource(wfile, rid, path):
    # the path are really for user's information only.
    # rid alone determines where to go.
    wlib = store.getMainBm()
    item = wlib.webpages.getById(rid)
    if not item:
        wfile.write('404 not found\r\n\r\n%s not found' % rid)
        return

    wlib.visit(item)
    response.redirect(wfile, item.url)


def doTag(wfile, env, method, form, tid):
    wlib = store.getMainBm()
    # we only do category_collapse setting so far
    if form.has_key('category_collapse'):
        # suppose to do this only for POST
        value = form.getfirst('category_collapse').lower()
        flag = value=='on'
        log.debug('doTag setCategoryCollapse @%s %s' % (tid, flag))

        wlib.setCategoryCollapse(tid, flag)
        store.save(wlib)

        # response for debug only
        wfile.write('content-type: text/plain\r\n')
        wfile.write('cache-control: no-cache\r\n')
        wfile.write('\r\n')
        wfile.write('setCategoryCollapse @%s %s' % (tid, flag))

    else:
        # not supported
        response.redirect(wfile, request.WEBLIB_URL)


def queryWebLib(wfile, env, form, tag, querytxt):
    go_direct = form.getfirst('submit') == '>'
    if querytxt.endswith('>'):
        querytxt = querytxt[:-1]
        go_direct = True

    wlib = store.getMainBm()
    tags, _ = weblib.parseTags(wlib, tag)
    items, related, most_visited = weblib.query(wlib, querytxt, tags)
    if querytxt:
        tags_matched = weblib.query_tags(wlib, querytxt, tags)
        tags_matched = [t.name for t in tags_matched]
    else:
        tags_matched = ()

    ##related hack
    parents = []
##    print >>sys.stderr, related
##    if related and hasattr(related, '__len__'):
##        parents = [t.tag for score,t in related[0]]
##        related  = [t for score,t in related[0]] + ['c'] + \
##            [t for score, t in related[1]] + ['r'] + \
##            [t for score, t in related[2]]
    # TODO: clean up what is related???
    related = []

    # quick jump?
    if go_direct and most_visited:
        wlib.visit(most_visited)
        response.redirect(wfile, most_visited.url)
        return

    folderNames = map(unicode, related)
    currentCategory = tags and unicode(tags[-1]) or ''
    categoryList = []
    top_nodes = wlib.category.root[1]
    for node in top_nodes:
        subcat = []
        tag = node[0]
        id = hasattr(tag,'id') and tag.id or -1
        categoryList.append((id, unicode(tag), subcat))
        for v, path in graph.dfsp(node):
            subcat.append((len(path),unicode(v)))

    all_items = []
    for tags, lst in sorted(items.items()):
        tags = sets.Set(tags).difference(parents)
        for l in lst:
            all_items.append((l,tags))
            tags = ()

    cc_lst = wlib.getCategoryCollapseList()
    defaultTag = unicode(wlib.getDefaultTag())
    if wlib.category.uncategorized:
        subcats = [(2, unicode(t)) for t in wlib.category.uncategorized]
        categoryList.append((-1, 'TAG', subcats))

    WeblibRenderer(wfile, env, querytxt).output(
        cc_lst,
        defaultTag,
        categoryList,
        most_visited,
        folderNames,
        tags_matched,
        currentCategory,
        all_items)



# ----------------------------------------------------------------------

class WeblibRenderer(response.CGIRendererHeadnFoot):
    TEMPLATE_FILE = 'weblib.html'
    """ weblib.html 2005-10-14
    con:category_collapse_init
    con:header
    con:rootTag
    con:defaultTag
    rep:catList
            con:toggleSwitch
            con:link
            con:subcat
                    rep:catItem
                            con:link
    con:no_match_msg
    con:web_items
            rep:crumb
                    con:link
            con:go_hint
                    con:address
            con:tags_matched
                    rep:tag
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
    def render(self, node,
        category_collapse,
        defaultTag,
        categoryList,
        most_visited,
        folderNames,
        tags_matched,
        currentCategory,
        webItems,
        ):
        """
        @param category_collapse - list of tag ids to collapse
        @param categoryList - list of (id, nodename, subcat) where
            subcat is list of (level, nodename)
        """

        # default Tag
        node.defaultTag.atts['href'] = request.tag_url([defaultTag])
        node.defaultTag.content = defaultTag
        if currentCategory == defaultTag:
            node.defaultTag.atts['class'] = 'CurrentCat'

        # category
        node.catList.repeat(self.renderCatItem, categoryList, currentCategory, category_collapse)

        # no match message
        if not webItems and not tags_matched:
            node.web_items.omit()
#            t = string.Template(node.no_match_msg.content)
#            node.no_match_msg.content = t.safe_substitute(querytxt=self.querytxt)
            return

        node.no_match_msg.omit()

        # most visited
        if not most_visited:
            node.web_items.go_hint.omit()
        else:
            node.web_items.go_hint.address.atts['href'] = request.go_url(most_visited)
            node.web_items.go_hint.address.content = most_visited.name

        # matched webItems
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

    def renderCatItem(self, node, item, currentCategory, category_collapse):
        id, cat, subcat = item
        collapse = id in category_collapse
        node.toggleSwitch.atts['id'] = '@%s' % id
        node.toggleSwitch.content = collapse and '+' or '-'
        node.link.content = cat
        if id > 0:
            node.link.atts['href'] = request.tag_url(cat)
            if cat == currentCategory:
                node.link.atts['class'] = 'CurrentCat'
        else:
            # otherwise it is a pseudo tag
            del node.link.atts['href']
        node.subcat.atts['class'] =  collapse and 'subcategoriesCollapsed'  or 'subcategories'
        node.subcat.catItem.repeat(self.renderSubCat, subcat, currentCategory)

    def renderSubCat(self, node, item, currentCategory):
        level, name = item
        if level > 1:
            node.atts['class'] = 'SubCat2'
        node.link.content = name
        node.link.atts['href'] = request.tag_url(name)
        if name == currentCategory:
            node.link.atts['class'] = 'CurrentCat'


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