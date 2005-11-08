import cgi
import logging
import os, sys
import sets
import string
import urllib
from xml.sax import saxutils

from minds.config import cfg
from minds.cgibin import weblibSnapshot
from minds.cgibin import weblibForm
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import graph
from minds.weblib import query_wlib
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

        if tag:
            queryTag(wfile, env, form, tag)
        else:
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


class CategoryNode:

    BEGIN_HIGHLIGHT = object()

    END_HIGHLIGHT = object()

    def __init__(self, tagOrName):
        self.tagName = unicode(tagOrName)
        if isinstance(tagOrName, weblib.Tag):
            self.id = tagOrName.id
        else:
            wlib = store.getMainBm()
            tag = wlib.tags.getByName(tagOrName)
            self.id = tag and tag.id or -1
        self.level = 0
        self.comma = False
        self.highlight = False


def _buildCategoryList(wlib, selectTag=''):
    """
    Build two level category list from wlib.category.

    @returns list of (catNode, [catNode])
    """
    lselectTag = selectTag.lower()
    categoryList = []

    top_nodes = wlib.category.root.children
    for node in top_nodes:
        # TODO: check highlight
        catNode = CategoryNode(node.data)
        subcats = []
        categoryList.append((catNode, subcats))

        if catNode.tagName.lower() == lselectTag:
            catNode.highlight = True

        highlight_path = []
        for node, path in node.dfs():
            if not path: continue
            name = unicode(node)
            subcat = CategoryNode(name)
            subcat.level = len(path)
            if not highlight_path:
                if name.lower() == lselectTag:
                    highlight_path = path[:] + [node]
                    subcats.append(CategoryNode.BEGIN_HIGHLIGHT)
            else:
                if highlight_path != path[:len(highlight_path)]:
                    highlight_path = []
                    subcats.append(CategoryNode.END_HIGHLIGHT)
            subcats.append(subcat)
        if highlight_path:
            subcats.append(CategoryNode.END_HIGHLIGHT)

        # add comma up second last item
        for i in range(len(subcats)-1):
            n = subcats[i]
            if n == CategoryNode.BEGIN_HIGHLIGHT or n == CategoryNode.END_HIGHLIGHT:
                continue
            n.comma = True

    if wlib.category.uncategorized:
        subcats = [CategoryNode(t) for t in wlib.category.uncategorized]
        categoryList.append((CategoryNode('TAG'), subcats))

    return categoryList


def n_dfs(root, nlist=None):
    # a version of dfs that yield item numbering

    if nlist is None:
        nlist = []   # create a new initial nlist list

    yield root, nlist
    nlist.append(0)
    for i, child in enumerate(root.children):
        nlist[-1] = i+1
        for x in n_dfs(child, nlist): yield x
    nlist.pop()


def queryTag(wfile, env, form, tag):
    wlib = store.getMainBm()
    branches = query_wlib.query_by_tag(wlib, tag)

    tags = [tag] ## hack
    currentCategory = tags and unicode(tags[-1]) or ''
    categoryList = _buildCategoryList(wlib, tag)

    all_items = []
#    for node, path in branches.dfs():
    for node, nlist in n_dfs(branches):
        name, result = node.data
        tag = wlib.tags.getByName(name)
        prefix = '.'.join(map(str,nlist))
        all_items.append((tag, prefix))
        for item in result:
            all_items.append((item, item.tags))

    cc_lst = wlib.getCategoryCollapseList()
    defaultTag = unicode(wlib.getDefaultTag())

    WeblibRenderer(wfile, env, '').output(
        cc_lst,
        defaultTag,
        categoryList,
        None,
        [],
        currentCategory,
        all_items)



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

    # quick jump?
    if go_direct and most_visited:
        wlib.visit(most_visited)
        response.redirect(wfile, most_visited.url)
        return

    currentCategory = tags and unicode(tags[-1]) or ''
    categoryList = _buildCategoryList(wlib)

    all_items = []
    for tags, lst in sorted(items.items()):
        tags = sets.Set(tags).difference(parents)
        for l in lst:
            all_items.append((l,tags))
            tags = ()

    cc_lst = wlib.getCategoryCollapseList()
    defaultTag = unicode(wlib.getDefaultTag())

    WeblibRenderer(wfile, env, querytxt).output(
        cc_lst,
        defaultTag,
        categoryList,
        most_visited,
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
        tags_matched,
        currentCategory,
        webItems,
        ):
        """
        @param category_collapse - list of tag ids to collapse
        @param webItems - list of (WebPage, [tags])
        """

        # ------------------------------------------------------------------------
        # default Tag
        node.defaultTag.atts['href'] = request.tag_url([defaultTag])
        node.defaultTag.content = defaultTag
        if currentCategory == defaultTag:
            node.defaultTag.atts['class'] = 'highlight'

        # category
        node.catList.repeat(self.renderCatItem, categoryList, currentCategory, category_collapse)

        # ------------------------------------------------------------------------
        # no match message
        if not webItems and not tags_matched:
            node.web_items.omit()
            return

        node.no_match_msg.omit()

        # most visited
        if not most_visited:
            node.web_items.go_hint.omit()
        else:
            node.web_items.go_hint.address.atts['href'] = request.go_url(most_visited)
            node.web_items.go_hint.address.content = most_visited.name

        # ------------------------------------------------------------------------
        # matched webItems
        if not tags_matched:
            node.web_items.tags_matched.omit()
        else:
            node.web_items.tags_matched.tag.repeat(self.renderTagsmatched, tags_matched)

        headerTemplate = node.web_items.headerTemplateHolder.headerTemplate
        # headerTemplateHolder is only a holder for headerTemplate, hide it
        node.web_items.headerTemplateHolder.omit()

        node.web_items.webItem.repeat(self.renderWebItem, enumerate(webItems), headerTemplate)


    def renderTagsmatched(self, node, tag):
        node.content = tag
        node.atts['href'] = request.tag_url(tag)


    def renderCatItem(self, node, item, currentCategory, category_collapse):
        catNode, subcats = item
        collapse = catNode.id in category_collapse
        node.toggleSwitch.atts['id'] = '@%s' % catNode.id
        node.toggleSwitch.content = collapse and '+' or '-'
        node.link.content = catNode.tagName
        if catNode.id > 0:
            node.link.atts['href'] = request.tag_url(catNode.tagName)
            if catNode.tagName.lower() == currentCategory.lower():
                node.atts['class'] = 'highlight'
        else:
            # otherwise it is a pseudo tag
            del node.link.atts['href']
        node.subcat.atts['class'] =  collapse and 'subcategoriesCollapsed'  or 'subcategories'
        node.subcat.catItem.repeat(self.renderSubCat, subcats, currentCategory)


    def renderSubCat(self, node, catNode, currentCategory):
        if catNode == CategoryNode.BEGIN_HIGHLIGHT:
            node.omittags()
            node.link.omittags()
            node.link.raw="<span class='highlight'>"
        elif catNode == CategoryNode.END_HIGHLIGHT:
            node.omittags()
            node.link.omittags()
            node.link.raw='</span>'
        else:
            if catNode.level > 1:
                node.atts['class'] = 'SubCat2'
            node.link.content = catNode.tagName + (catNode.comma and ',' or '')
            node.link.atts['href'] = request.tag_url(catNode.tagName)
            if catNode.tagName.lower() == currentCategory.lower():
                node.link.atts['class'] = 'highlight'


    def renderWebItem(self, node, item, headerTemplate):
        i, (item, tags) = item
        node.atts['class'] = i % 2 and 'altrow' or ''

        if isinstance(item, weblib.WebPage):
            node = node.placeHolder
            node.checkbox.atts['name'] = str(item.id)
            node.itemDescription.content = unicode(item)
            node.itemDescription.atts['href'] = request.go_url(item)
            node.itemDescription.atts['title'] = saxutils.quoteattr('%s %s' % (item.modified, item.description))[1:-1]
            # TODO HACK, should fix HTMLTemplate which reject string with both single and double quote
            node.itemTag.tag.repeat(self.renderWebItemTag, tags)
            node.edit.atts['href'] = '%s/%s/form' % (request.WEBLIB_URL, item.id)
            node.delete.atts['href'] = '%s/%s?method=delete' % (request.WEBLIB_URL, item.id)
            if item.cached:
                node.cache.atts['href'] = '%s/%s/snapshotFrame' % (request.WEBLIB_URL, item.id)
                node.cache.content = item.cached
            else:
                node.cache.atts['href'] = '%s/%s/snapshot/get' % (request.WEBLIB_URL, item.id)
                node.cache.content = 'download'
        else:
            node.placeHolder = headerTemplate
            node.placeHolder.prefix.content = tags
            node.placeHolder.itemHeader.content = unicode(item)
            node.placeHolder.itemHeader.atts['href'] = request.tag_url([item])


    def renderWebItemTag(self, node, tag):
        node.content = unicode(tag)
        node.atts['href'] = request.tag_url([tag])


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)