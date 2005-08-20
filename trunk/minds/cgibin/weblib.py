import cgi
#import datetime
import logging
import os, sys
import sets
#import string
import urllib

from minds.config import cfg
from minds.cgibin import weblibEdit
from minds.cgibin.util import response
from minds import weblib
#from minds.weblib import store
from minds.weblib import graph

log = logging.getLogger('cgi.weblib')

BASEURL = 'weblib'


"""
weblib                      show home page

weblib?tag=xx,yy            show tag

weblib?query=xx&tag=yy      search xx

weblib/_                    show edit screen        PUT weblib/_
weblib/%id                                          PUT weblib/%id            
                                                    redirect weblib?tag=xx,yy    
    view=?
    field=?                   
                                                             
                                                    DELETE weblib/%id
                                                    redirect weblib?tag=xx,yy    

weblib/%id/go;http://xyz    Redirect to page

weblib/%id/cache
weblib/%id/cache&cid=

"""


def main(rfile, wfile, env):

    method, action, rid, go_part, tag, querytxt, form = parseURL(rfile, env)

    log.debug('method %s action %s rid %s', method, action, rid)

    if action == 'cancel':
        redirect(wfile,'')
        
    elif go_part:
        doGoResource(wfile, rid, go_part)
        
    elif querytxt:
        queryWebLib(wfile, env, form, tag, querytxt)
        
    elif rid is not None:
        weblibEdit.main(rfile, wfile, env, method, form, rid)
        
    else:
        queryWebLib(wfile, env, form, tag, '')


def parseURL(rfile, env):
    """ 
    @return method, rid, tag, view, querytxt, form
        method - 'GET', 'PUT', 'DELETE' 
        action - the value from the submit button
        rid - None: n/a; '_': new item; int: resource id                
        go_part
        tag - string of comma seperated tags
        view - view parameter ('XML', '', etc. ???)
        querytxt - querytxt parameter
        form - cgi.FieldStorage
    """  

    form = cgi.FieldStorage(fp=rfile, environ=env)

    # parse resource id (None, -1, int)
    # also get go_part
    resources = env.get('PATH_INFO', '').strip('/').split('/',1)
    resource = resources[0]
    rid = None
    go_part = ''
    if resource == '_':
        rid = -1
    else:
        try:
            rid = int(resource)
        except ValueError: 
            pass
        if rid and len(resources) > 1:
            if resources[1].startswith('go;'):
                go_part = resources[1]

    # the edit form can only do GET, use 'action' as an alternative
    method = env.get('REQUEST_METHOD','GET')
    action = form.getfirst('action', '').lower()
    if action == 'ok':
        method = 'PUT'
    elif action == 'delete':
        method = 'DELETE'
    elif form.getfirst('create_tags',''):
        # note: in this case the javascript:form.submit() has trouble setting
        # a value for the action <input>. We assume create_tags implies PUT.
        method = 'PUT'
        
    method = method.upper()

    # other parameters
    tag  = form.getfirst('tag','').decode('utf-8')
    querytxt  = form.getfirst('query','').decode('utf-8')

    return method, action, rid, go_part, tag, querytxt, form


def doGoResource(wfile, rid, go_part):
    # the go_part are really for user's information only. 
    # rid alone determines where to go.
    wlib = weblib.getMainBm()
    item = wlib.webpages.getById(rid)
    if not item:
        wfile.write('404 not found\r\n\r\n%s not found' % rid)
        return

    wlib.visit(item)
    redirect(wfile, '', url=item.url)        



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

    if go_direct and most_visited:
        # quick jump
        wlib.visit(most_visited)
        redirect(wfile, '', url=most_visited.url)
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
    


def redirect(wfile, tags, url=''):    # TODO: refactor parameters
    if url:
        wfile.write('location: %s\r\n\r\n' % (url,))
    elif tags: 
        wfile.write('location: %s\r\n\r\n' % make_tag_url(tags))
    else:
        wfile.write('location: /%s\r\n\r\n' % (BASEURL,))


def make_go_url(item):
    return '/%s/%s/go;%s' % (BASEURL, item.id, item.url)
    

def make_tag_url(tags):
    if hasattr(tags,'encode'):##??
        qs = unicode(tags)    
    else:
        qs = u','.join(map(unicode, tags))
    qs = urllib.quote_plus(qs.encode('utf8'))
    return '/%s?tag=%s' % (BASEURL, qs)


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
            node.go_hint.address.atts['href'] = make_go_url(most_visited)
            node.go_hint.address.content = most_visited.name
                    
        node.crumb.repeat(self.renderCrumb, folderNames)

        node.catList.repeat(self.renderCatItem, categoryList, currentCategory)

        node.webItem.repeat(self.renderWebItem, webItems)

    def renderCrumb(self, node, item):
        node.link.content = item
        node.link.atts['href'] = make_tag_url(item)

    def renderCatItem(self, node, item, currentCategory):
        cat, subcat = item
        node.link.content = cat
        node.link.atts['href'] = make_tag_url(cat)
        if cat == currentCategory:
            node.link.atts['class'] = 'CategoryCurrentItem'
        node.catItem.repeat(self.renderSubCat, subcat, currentCategory)

    def renderSubCat(self, node, item, currentCategory):
        node.link.content = item
        node.link.atts['href'] = make_tag_url(item)
        if item == currentCategory:
            node.link.atts['class'] = 'CategoryCurrentItem'

    def renderWebItem(self, node, item):
        item, tags = item   ##todo
        node.checkbox.atts['name'] = str(item.id)
        node.itemDescription.content = unicode(item)
        node.itemDescription.atts['href'] = make_go_url(item)
        node.itemTag.tag.repeat(self.renderWebItemTag, tags)
        node.edit.atts['href'] = '/%s/%s?view=edit' % (BASEURL, item.id)
        node.delete.atts['href'] = '/%s/%s?action=delete' % (BASEURL, item.id)
        node.cache.atts['href'] = '/%s/%s?view=edit' % (BASEURL, item.id)

    def renderWebItemTag(self, node, tag):
        node.content = unicode(tag)
        node.atts['href'] = make_tag_url([tag])


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)