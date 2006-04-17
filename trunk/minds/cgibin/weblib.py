import cgi
import logging
import os, sys
import sets
import string
import urllib

from minds.config import cfg
from minds import upgrade_checker
from minds.cgibin import weblibSnapshot
from minds.cgibin import weblibForm
from minds.cgibin import weblibTagForm
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import graph
from minds.weblib import query_wlib
from minds.weblib import store
from minds.weblib import util

log = logging.getLogger('cgi.weblib')


def _tag_from_cookie(req):
    tid = req.cookie.get('weblib_tag')
    if not tid:
        return None
    tid = tid.value
    try:
        if not tid.startswith('@'):
            return None
        tid = int(tid[1:])
    except ValueError:
        return None
    wlib = store.getWeblib()
    return wlib.tags.getById(tid)


class SORT:
    """ A namespace and helper methods """
    ASC  = 'asc'
    DESC = 'desc'

    TITLE = 'title'
    TAG   = 'tag'
    DATE  = 'date'

    TITLE_ASC  = TITLE + '-' + ASC
    TITLE_DESC = TITLE + '-' + DESC
    TAG_ASC    = TAG   + '-' + ASC
    TAG_DESC   = TAG   + '-' + DESC
    DATE_ASC   = DATE  + '-' + ASC
    DATE_DESC  = DATE  + '-' + DESC

    TOKENS = [
        TITLE_ASC ,
        TITLE_DESC,
        TAG_ASC   ,
        TAG_DESC  ,
        DATE_ASC  ,
        DATE_DESC ,
    ]

    @staticmethod
    def parse_token(token):
        """ Parse 'column-order' into (column, order) """
        if token not in SORT.TOKENS:
            return '',''
        return token.split('-',1)


def _get_sort_preference(req):
    # note: it is possible for sort to be unspecified
    #print >>sys.__stderr__, req.param('sort'), '<>', req.cookie.get('weblib_sort')#, req
    if 'sort' in req.form:
        sort = req.param('sort')
    elif 'weblib_sort' in req.cookie:
        sort = req.cookie.get('weblib_sort').value
    else:
        return ''
    sort = sort.lower()
    if sort not in SORT.TOKENS:
        return ''
    return sort


def main(rfile, wfile, env):
    wlib = store.getWeblib()

    req = request.WeblibRequest(rfile, env)
    log.debug(unicode(req))
    path = req.path

    if req.rid:
        # rid based (note rid maybe -1)
        if path and path.startswith('go;'):
            doGoResource(wfile, req)
        elif path and path == 'url':
            doLaunchURL(wfile, req)
        elif path and path.startswith('snapshot'):
            weblibSnapshot.main(wfile, env, req.method, req.form, req.rid, path)
        elif path == 'form':
            doWeblibForm(wfile, req)
        else:
            # show form by default
            doWeblibForm(wfile, req)

    elif req.tid:
        doweblibTagForm(wfile, req)

    else:
        if path == 'load':
            doLoad(wfile, req)
        elif path == 'save':
            doSave(wfile, req)
        else:
            doQuery(wfile, req)


def doQuery(wfile, req):
    wlib = store.getWeblib()
    querytxt = req.param('query')
    tag = req.param('tag')
    sort = _get_sort_preference(req)
    # No tag specified? Use fallback: 1. cookie, 2. default tag
    if not ('tag' in req.form or querytxt):
        def_tag = _tag_from_cookie(req) or wlib.getDefaultTag()
        if def_tag:
            url = request.tag_url([def_tag])
            if sort:
                url = '%s&sort=%s' % (url, sort)
            response.redirect(wfile, url)
            return

    if tag:
        queryTag(wfile, req, tag, sort)
    elif querytxt:
        queryWebLib(wfile, req, tag, sort, querytxt)
    else:
        queryRoot(wfile, req, sort)


def doWeblibForm(wfile, req):
    try:
        reload(weblibForm)  # reload for development convenience
    except:
        pass                # doesn't work in py2exe service version. But it's OK.
    # delegate to another CGI variant
    weblibForm.main(wfile, req)


def doweblibTagForm(wfile, req):
    try:
        reload(weblibTagForm)   # reload for development convenience
    except:
        pass                    # doesn't work in py2exe service version. But it's OK.
    # delegate to another CGI variant
    weblibTagForm.main(wfile, req)


def doGoResource(wfile, req):
    # the path are really for user's information only.
    # rid alone determines where to go.
    wlib = store.getWeblib()
    item = wlib.webpages.getById(req.rid)
    if not item:
        wfile.write('404 not found\r\n\r\n%s not found' % req.rid)
        return

    item = wlib.visit(item)
    response.redirect(wfile, item.url)


def doLaunchURL(wfile, req):
    wlib = store.getWeblib()
    item = wlib.webpages.getById(req.rid)
    if not item:
        wfile.write('404 not found\r\n\r\n%s not found' % req.rid)
        return

    if util.isFileURL(item.url):
        # TODO: HACK win32 only??
        # TODO: It is dangerous to launch anything could be executable or script
        from minds.weblib.win32 import ntfs_util
        ntfs_util.launch(item.url)
        wfile.write('content-type: text/html\r\n')
        wfile.write('Cache-control: no-cache\r\n')
        wfile.write('\r\n')
        wfile.write('''<html>
<head>
  <script>window.close();</script>
</head>
<body>
  File launched in separate window. Please close this window.
</body>
</html>
        ''')
    else:
        response.redirect(wfile, item.url)


def doLoad(wfile, req):
    store.getStore().load()
    wlib = store.getWeblib()
    wfile.write('200 ok\r\n\r\n')
    wfile.write('Load %s pages %s tags' % (len(wlib.webpages), len(wlib.tags)))


def doSave(wfile, req):
    store.getStore().save_and_backup()
    wlib = store.getWeblib()
    wfile.write('200 ok\r\n\r\n')
    wfile.write('saved %s pages %s tags' % (len(wlib.webpages), len(wlib.tags)))



# ------------------------------------------------------------------------

class CategoryNode(object):
    """ An object to be shown on the category pane """

    BEGIN_HIGHLIGHT = object()

    END_HIGHLIGHT = object()

    def __init__(self, tagOrName):
        self.tagName = unicode(tagOrName)
        if isinstance(tagOrName, weblib.Tag):
            self.id = tagOrName.id
            self.tag = tagOrName
        else:
            wlib = store.getWeblib()
            self.tag = wlib.tags.getByName(tagOrName)
            self.id = self.tag and self.tag.id or -1
        self.level = 0
        self.comma = False
        self.highlight = False

    def __repr__(self):
        return '.'* self.level + self.tagName


class WebItemNode(object):
    """ An object to be shown on the web item pane """
    def __init__(self, webitem):
        self.webitem = webitem


class WebItemTagNode(object):
    """ An object to be shown on the web item pane """
    def __init__(self, tag):
        self.tag = tag
        self.prefix = ''
        self.suffix = ''


def _buildCategoryList(wlib, selectTag=''):
    """
    Build two level category list from wlib.category.

    @returns list of (catNode, [descendant catNode])
    """
    defaultTag = wlib.getDefaultTag()
    lselectTag = selectTag.lower()
    categoryList = []

    top_nodes = wlib.category.root.children
    for top_node in top_nodes:
        # TODO: check highlight
        catNode = CategoryNode(top_node.data)
        subcats = []
        categoryList.append((catNode, subcats))

        if catNode.tagName.lower() == lselectTag:
            catNode.highlight = True

        # use to determine if the node is within a highlighted subtree
        # if highlight_path is a prefix of node's path then it should be highlighted.
        highlight_path = []

        for node, path in top_node.dfs():
            if not path: continue
            tag = node.data
            subcat = CategoryNode(tag)
            subcat.level = len(path)
            if not highlight_path:
                if tag.match(lselectTag):
                    highlight_path = path[:] + [node]
                    subcats.append(CategoryNode.BEGIN_HIGHLIGHT)
            else:
                if highlight_path != path[:len(highlight_path)]:
                    highlight_path = []
                    subcats.append(CategoryNode.END_HIGHLIGHT)
            subcats.append(subcat)
        if highlight_path:
            subcats.append(CategoryNode.END_HIGHLIGHT)

        # add comma up to second last item
        tag_nodes = [node for node in subcats
            if node not in (CategoryNode.BEGIN_HIGHLIGHT, CategoryNode.END_HIGHLIGHT)]
        for node in tag_nodes[:-1]:
            node.comma = True

    uncategorized = wlib.category.getUncategorized()
    if uncategorized:
        uncategorized_nodes = [CategoryNode(t) for t in uncategorized if not defaultTag.match(t)]
        if uncategorized_nodes:
            for node in uncategorized_nodes[:-1]:
                node.comma = True
            categoryList.append((CategoryNode('TAG'), uncategorized_nodes))

    return categoryList


def _n_dfs(root, nlist=None):
    # a version of dfs that yield item numbering

    if nlist is None:
        nlist = []   # create a new initial nlist list

    yield root, nlist
    nlist.append(0)
    for i, child in enumerate(root.children):
        nlist[-1] = i+1
        for x in _n_dfs(child, nlist): yield x
    nlist.pop()


def _query_by_tag(wlib, tag, sort):
    col, order = SORT.parse_token(sort)
    positions = query_wlib.query_by_tag(wlib, tag)

    # build and sort webItems
    webItems = []

    if col == SORT.TITLE or col == SORT.DATE:
        lst = []
        for pos in positions:
            for _,_,page in pos.items:
                if col == SORT.TITLE:
                    key = page.name.lower()
                else:
                    key = page.created
                lst.append((key,WebItemNode(page)))
        lst.sort(reverse=(order==SORT.DESC))
        webItems = [w for _,w in lst]

    else:
        # order by tag (default)
        for pos in positions:
            tagNode = WebItemTagNode(pos.tag)
            tagNode.prefix = pos.prefix
            webItems.append(tagNode)
            for _,_,page in pos.items:
                webItems.append(WebItemNode(page))

    return webItems


def queryTag(wfile, req, nameOrId, sort):
    wlib = store.getWeblib()

    tag = weblib.parseTag(wlib, nameOrId)
    tagName = tag and tag.name or ''

    # Note: URL is expected to have valid tag parameter. If it turns up
    # nothing, one possibility is user has entered an invalid URL
    # manually. In that case the query below should turn out empty
    # result. We choose not go for the alternative or redirecting user
    # to / or inbox because it seems even more confusing.

    # category pane
    categoryList = _buildCategoryList(wlib, tagName)

    # upgrade_info
    upgrade_info = upgrade_checker.pollUpgradeInfo()

    # webitem pane
    if tag:
        webItems = _query_by_tag(wlib, tag, sort)
    else:
        # TODO: HACK!!!
        # Create a fake tag to fill something in the result
        # Seems WeblibRenderer() is OK with this
        fakeTagNode = WebItemTagNode(nameOrId)
        webItems = [fakeTagNode]

    renderer = WeblibRenderer(wfile)
    if tag:
        renderer.cookie['weblib_tag'] = '@%s' % tag.id
    if sort:
        renderer.cookie['weblib_sort'] = sort
    renderer.setLayoutParam(None)
    renderer.output(
        request.tag_url(nameOrId),
        wlib.tags,
        tag,
        wlib.getDefaultTag(),
        categoryList,
        upgrade_info,
        sort,
        webItems,
        )


def queryWebLib(wfile, req, tag, sort, querytxt):
    go_direct = req.param('submit') == '>'
    if querytxt.endswith('>'):
        querytxt = querytxt[:-1]
        go_direct = True

    wlib = store.getWeblib()
    tags, _ = weblib.parseTags(wlib, tag)

    # query
    result = query_wlib.query(wlib, querytxt, tags)

    # quick jump?
    if go_direct and result:
        top_item = result[0][0]
        #top_item = wlib.visit(top_item)
        response.redirect(wfile, top_item.url)
        return

    # category pane
    categoryList = _buildCategoryList(wlib)
    tag = tags and wlib.getTagByName(tags[-1]) or None

    # upgrade_info
    upgrade_info = upgrade_checker.pollUpgradeInfo()

    # webitem pane
    webItems = []
    if querytxt:
        tags_matched = query_wlib.query_tags(wlib, querytxt, tags)
        for tag in tags_matched:
            node = WebItemTagNode(tag)
            node.suffix = '...'
            webItems.append(node)

    # sort result?
    col, order = SORT.parse_token(sort)
    if col == SORT.TITLE or col == SORT.DATE:
        lst = []
        for r in result:
            item = r[0]
            if col == SORT.TITLE:
                key = item.name.lower()
            else:
                key = item.created
            lst.append((key,r))
        lst.sort(reverse=(order==SORT.DESC))
        result = [r for _,r in lst]

    for item,_ in result:
        webItems.append(WebItemNode(item))

    # reconstuct the base url
    qs = urllib.quote_plus(querytxt.encode('utf8'))
    base_url = '/weblib?query=' + qs

    renderer = WeblibRenderer(wfile)
    if sort:
        renderer.cookie['weblib_sort'] = sort
    renderer.setLayoutParam(querytxt=querytxt)
    renderer.output(
        base_url,
        wlib.tags,
        None,
        wlib.getDefaultTag(),
        categoryList,
        upgrade_info,
        sort,
        webItems,
        )


def queryRoot(wfile, req, sort):
    wlib = store.getWeblib()

    # category pane
    categoryList = _buildCategoryList(wlib)

    # upgrade_info
    upgrade_info = upgrade_checker.pollUpgradeInfo()

    # webitem pane
    webItems = map(WebItemNode, query_wlib.queryRoot(wlib))

    renderer = WeblibRenderer(wfile)
    if sort:
        renderer.cookie['weblib_sort'] = sort
    renderer.setLayoutParam(None)
    renderer.output(
        '/weblib',
        wlib.tags,
        None,
        wlib.getDefaultTag(),
        categoryList,
        upgrade_info,
        sort,
        webItems,
        )


# ----------------------------------------------------------------------

class WeblibRenderer(response.WeblibLayoutRenderer):
    TEMPLATE_FILE = 'weblibContent.html'
    """ weblibContent.html 2006-04-17
    con:tagListForm
            rep:tag
    con:rootTag
    con:defaultTag
    rep:catList
            con:toggleSwitch
            con:link
            con:subcat
                    rep:catItem
                            con:link
    con:upgrade_notification
            con:link
                    con:title
                    con:summary
    con:found_msg
            con:search_engine
                    con:querytxt
                    rep:engine
            con:count
    con:web_items
            con:heading
                    con:tag
                            con:icon
                    con:title
                            con:icon
                    con:date
                            con:icon
                    con:edit
                    con:delete
            con:headerTemplateHolder
                    con:headerTemplate
                            con:prefix
                            con:itemHeader
            rep:webItem
                    con:placeHolder
                            con:checkbox
                            con:description
                            rep:tag
                            con:date
                            con:edit
                            con:delete
    """
    def render(self, node,
        base_url,
        tags,
        selectedTag,
        defaultTag,
        categoryList,
        upgrade_info,
        sort,
        webItems,
        ):
        """
        @param base_url - base URL that invoke this page (without the sort parameter)
        @param tags - list of all tags
        @param selectedTag - tag selected or None
        @param defaultTag - a Tag (e.g. inbox)
        @param webItems - sequence of intermixed WebItemNode and WebItemTagNode
        """

        lSelectedTagName = selectedTag and selectedTag.name.lower() or ''

        # ------------------------------------------------------------------------
        # tag list
        lst = [(tag.name.lower(), tag.name, tag.id) for tag in tags]
        lst = [(name,id) for _,name,id in sorted(lst)]
        lst = [('',None)] + lst
        node.tagListForm.atts['action'] = selectedTag and '/weblib/@%s' % selectedTag.id or ''
        node.tagListForm.tag.repeat(self.renderTag, lst, lSelectedTagName)


        # ------------------------------------------------------------------------
        # default Tag
        node.defaultTag.atts['href'] = request.tag_url([defaultTag])
        node.defaultTag.content = unicode(defaultTag)
        if defaultTag.match(selectedTag):
            node.defaultTag.atts['class'] = 'highlight'
# Actually need to make sure it is not doing search
#        if not lTagSelected:
#            node.rootTag.atts['class'] = 'highlight'

        # category
        node.catList.repeat(self.renderCatItem, categoryList, lSelectedTagName)

        # ------------------------------------------------------------------------
        # upgrade info
        if not upgrade_info:
            node.upgrade_notification.omit()
        else:
            node.upgrade_notification.link.atts['href']     = upgrade_info.url
            node.upgrade_notification.link.title.content    = upgrade_info.title
            node.upgrade_notification.link.summary.content  = upgrade_info.summary

        # ------------------------------------------------------------------------
        # Matching message
        count = sum(1 for item in webItems if isinstance(item, WebItemNode))
        node.found_msg.count.content = str(count)
        from minds import search_engine
        if search_engine.getEngines():
            node.found_msg.search_engine.engine.repeat(self.renderSearchEngine, search_engine.getEngines())
            node.found_msg.search_engine.querytxt.content = self.querytxt
        else:
            node.found_msg.search_engine.omit()

        if not webItems:
            node.web_items.omit()
            return

        # ------------------------------------------------------------------------
        # webitems Heading
        h = node.web_items.heading
        if '?' in base_url:
            base_url += '&sort=%s'
        else:
            base_url += '?sort=%s'

        if sort == SORT.TITLE_ASC:
            h.title.icon.atts['src'] = '/img/arrowUp.gif'
            h.title.atts['href'] = base_url % SORT.TITLE_DESC
        elif sort == SORT.TITLE_DESC:
            h.title.icon.atts['src'] = '/img/arrowDown.gif'
            h.title.atts['href'] = base_url % SORT.TITLE_ASC
        else:
            h.title.icon.omit();
            h.title.atts['href'] = base_url % SORT.TITLE_ASC

        if sort == SORT.TAG_ASC:
            h.tag.icon.atts['src'] = '/img/arrowUp.gif'
            h.tag.atts['href'] = base_url % SORT.TAG_ASC    # tag is only ordered one way
        elif sort == SORT.TAG_DESC:
            h.tag.icon.atts['src'] = '/img/arrowDown.gif'
            h.tag.atts['href'] = base_url % SORT.TAG_ASC
        else:
            h.tag.icon.omit();
            h.tag.atts['href'] = base_url % SORT.TAG_ASC

        if sort == SORT.DATE_ASC:
            h.date.icon.atts['src'] = '/img/arrowUp.gif'
            h.date.atts['href'] = base_url % SORT.DATE_DESC
        elif sort == SORT.DATE_DESC:
            h.date.icon.atts['src'] = '/img/arrowDown.gif'
            h.date.atts['href'] = base_url % SORT.DATE_ASC
        else:
            h.date.icon.omit();
            h.date.atts['href'] = base_url % SORT.DATE_ASC

        # ------------------------------------------------------------------------
        # webitems
        headerTemplate = node.web_items.headerTemplateHolder.headerTemplate
        # headerTemplateHolder is only a holder for headerTemplate, hide it
        node.web_items.headerTemplateHolder.omit()

        node.web_items.webItem.repeat(self.renderWebItem, enumerate(webItems), headerTemplate)


    def renderTag(self, node, item, lSelectedTagName):
        name, id = item
        node.atts['value'] = id and '@%s' % id or ''
        if name.lower() == lSelectedTagName:
            node.atts['selected'] = '1'
        node.content = name


    def renderCatItem(self, node, item, lSelectedTagName):
        catNode, subcats = item
        isCurrent = catNode.tagName.lower() == lSelectedTagName
        iscollapse = not isCurrent and catNode.tag and ('c' in catNode.tag.flags)
        node.toggleSwitch.atts['id'] = '@%s' % catNode.id
        node.toggleSwitch.content = iscollapse and '+' or '-'
        node.link.content = catNode.tagName
        if catNode.id > 0:
            node.link.atts['href'] = request.tag_url(catNode.tagName)
            if isCurrent:
                node.atts['class'] = 'highlight'
        else:
            # otherwise it is a pseudo tag
            del node.link.atts['href']
        node.subcat.atts['class'] =  iscollapse and 'subcategoriesCollapsed'  or 'subcategories'
        node.subcat.catItem.repeat(self.renderSubCat, subcats, lSelectedTagName)


    def renderSubCat(self, node, catNode, lSelectedTagName):
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
            if  catNode.tagName.lower() == lSelectedTagName:
                node.link.atts['class'] = 'highlight'


    def renderSearchEngine(self, node, engine):
        node.atts['href'] = engine.url.replace('%s',self.querytxt.encode('utf8'))
        node.content = engine.label


    def renderWebItem(self, node, item, headerTemplate):
        i, webItemNode = item
        node.atts['class'] = i % 2 and 'altrow' or ''

        if isinstance(webItemNode, WebItemNode):
            webitem = webItemNode.webitem
            node = node.placeHolder
            node.checkbox.atts['name'] = str(webitem.id)
            node.description.content = unicode(webitem)
            if util.isFileURL(webitem.url):
                href = 'javascript:open_url(%s,"%s")' % (webitem.id, webitem.url)
                node.description.atts['href'] = href
            else:
                node.description.atts['href'] = webitem.url
            node.description.atts['title'] = '%s %s' % (webitem.modified, webitem.description)
            node.tag.repeat(self.renderWebItemTag, webitem.tags)
            node.date.content = webitem.created or '0000-00-00'
            node.edit.atts['href'] %= webitem.id
            node.delete.atts['href'] = '%s/%s?method=delete' % (request.WEBLIB_URL, webitem.id)
#            if webitem.fetched:
#                node.cache.atts['href'] = '%s/%s/snapshotFrame' % (request.WEBLIB_URL, webitem.id)
#                node.cache.content = webitem.fetched
#            else:
#                node.cache.atts['href'] = '%s/%s/snapshot/get' % (request.WEBLIB_URL, webitem.id)
#                node.cache.content = 'download'
        else:
            tag = webItemNode.tag
            node.placeHolder = headerTemplate
            node.placeHolder.prefix.content = webItemNode.prefix
            node.placeHolder.itemHeader.content = unicode(tag) + webItemNode.suffix
            node.placeHolder.itemHeader.atts['href'] = request.tag_url([tag])


    def renderWebItemTag(self, node, tag):
        node.content = unicode(tag)
        node.atts['href'] = request.tag_url([tag])


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)