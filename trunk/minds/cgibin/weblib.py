import cgi
import logging
import os, sys
import sets
import urllib

from minds.config import cfg
from minds.cgibin import weblibForm
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import graph

log = logging.getLogger('cgi.weblib')


def main(rfile, wfile, env):
    method, form, rid, rid_path = request.parseURL(rfile, env)
    log.debug('method %s rid %s', method, rid)

    # other parameters
    tag = form.getfirst('tag','').decode('utf-8')
    querytxt  = form.getfirst('query','').decode('utf-8')

    if form.getfirst('action ') == 'cancel':
        request.redirect(wfile, request.WEBLIB_URL)
        
    elif rid_path and rid_path.startswith('go;'):
        doGoResource(wfile, rid, rid_path)
        
    elif querytxt:
        queryWebLib(wfile, env, form, tag, querytxt)
        
    elif rid is not None:
        weblibForm.main(rfile, wfile, env, method, form, rid)
        
    else:
        queryWebLib(wfile, env, form, tag, '')



def doGoResource(wfile, rid, rid_path):
    # the rid_path are really for user's information only. 
    # rid alone determines where to go.
    wlib = weblib.getMainBm()
    item = wlib.webpages.getById(rid)
    if not item:
        wfile.write('404 not found\r\n\r\n%s not found' % rid)
        return

    wlib.visit(item)
    request.redirect(wfile, item.url)        



def queryWebLib(wfile, env, form, tag, querytxt):
    go_direct = form.getfirst('submit') == '>'
    if querytxt.lower().startswith('g '):
        querytxt = querytxt[2:]
        go_direct = True
    
    wlib = weblib.getMainBm()   

    tags, unknown = weblib.parseTags(wlib, tag)
    items, related, most_visited = weblib.query(wlib, querytxt, tags)

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
        request.redirect(wfile, most_visited.url)
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
    WeblibRenderer(wfile, env, querytxt).output(most_visited, folderNames, categoryList, currentCategory, all_items)



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
    def render(self, node, most_visited, folderNames, categoryList, currentCategory, webItems):
        
        if not most_visited:
            node.go_hint.omit()
        else:    
            node.go_hint.address.atts['href'] = request.go_url(most_visited)
            node.go_hint.address.content = most_visited.name
                    
        node.crumb.repeat(self.renderCrumb, folderNames)

        node.catList.repeat(self.renderCatItem, categoryList, currentCategory)

        node.webItem.repeat(self.renderWebItem, webItems)

    def renderCrumb(self, node, item):
        node.link.content = item
        node.link.atts['href'] = request.tag_url(item)

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

    def renderWebItem(self, node, item):
        item, tags = item   ##todo
        node.checkbox.atts['name'] = str(item.id)
        node.itemDescription.content = unicode(item)
        node.itemDescription.atts['href'] = request.go_url(item)
        node.itemTag.tag.repeat(self.renderWebItemTag, tags)
        node.edit.atts['href'] = '%s/%s/form' % (request.WEBLIB_URL, item.id)
        node.delete.atts['href'] = '%s/%s?method=delete' % (request.WEBLIB_URL, item.id)
        node.cache.atts['href'] = '%s/%s/cache' % (request.WEBLIB_URL, item.id)

    def renderWebItemTag(self, node, tag):
        node.content = unicode(tag)
        node.atts['href'] = request.tag_url([tag])


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)