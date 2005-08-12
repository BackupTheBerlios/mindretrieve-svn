#import codecs
import cgi
import datetime
import logging
import os, sys
import sets
import urllib

from minds.config import cfg
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import store
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


class Bean(object):
    
    def __init__(self, rid, form):
        self.rid = rid
        self.form = form     
        self.item = None

        # tags string. This is tentative and may contain new tags.
        self.tags = ''
        self.related = ''
        
        # tags not known
        self.newTags = sets.Set()
        self.create_tags = self.form.getfirst('create_tags','').decode('utf-8')
        
        self.errors = []
        
        self._readForm(rid, form)


    def _readForm(self, rid, form):
        wlib = weblib.getMainBm()
        
        if form.has_key('filled'):
            item = weblib.WebPage(
                id          = rid,
                name        = form.getfirst('t','').decode('utf-8'),
                url         = form.getfirst('u','').decode('utf-8'),
                description = form.getfirst('ds','').decode('utf-8'),
                modified    = form.getfirst('modified','').decode('utf-8'),
                lastused    = form.getfirst('lastused','').decode('utf-8'),
                cached      = form.getfirst('cached','').decode('utf-8'),
            )
            self.item = item

            self._parseTags()

        else:    
            item = wlib.webpages.getById(rid)
            if item:
                # make a copy of existing item    
                item = item.__copy__()
            else:    
                item = wlib.newWebPage(
                    name        = form.getfirst('t','').decode('utf-8'),
                    url         = form.getfirst('u','').decode('utf-8'),
                    description = form.getfirst('ds','').decode('utf-8'),
                )
                
            self.item = item
            self.tags  = ', '.join([l.name for l in item.tags])
            self.related = ', '.join([l.name for l in item.related])
        

    def _parseTags(self):
        wlib = weblib.getMainBm()

        _tags = self.form.getfirst('tags','').decode('utf-8')
        self.item.tags, unknown_tags = weblib.parseTags(wlib, _tags)
        self.item.tagIds = [l.id for l in self.item.tags]

        _related = self.form.getfirst('related','').decode('utf-8')
        self.item.related, unknown_related = weblib.parseTags(wlib, _related)
        self.item.relatedIds = [l.id for l in self.item.related]
        
        self.tags = _tags
        self.related = _related
        self.newTags = sets.Set()
        self.newTags.union_update(unknown_tags)
        self.newTags.union_update(unknown_related)
        
        
    def validate(self):
        if not self.item.name:
            self.errors.append('Please enter a name.')    
        if not self.item.url:
            self.errors.append('Please enter an address.')    
        if self.newTags and not self.create_tags:
            tags = u', '.join(self.newTags)
            self.errors.append('These tags are not previous used: ' + tags)
        return not self.errors


    def __str__(self):
        if not self.item: 
            return 'None'
        else:        
            return u'%s(%s)' % (self.item.name, self.item.rid)

    
def main(rfile, wfile, env):

    method, action, rid, go_part, tag, querytxt, form = parseURL(rfile, env)

    log.debug('method %s action %s rid %s', method, action, rid)

    if action == 'cancel':
        redirect(wfile,'')
        
    elif go_part:
        doGoResource(wfile, rid, go_part)
        
    elif querytxt:
        queryWebLib(wfile, env, form, tag, querytxt)
        
    elif rid == None:
        queryWebLib(wfile, env, form, tag, '')
        
    else:    
        # build bean from rid and other form parameters
        bean = Bean(rid, form)
        if method == 'GET':
            doGetResource(wfile, bean, None)
        elif method == 'PUT':
            doPutResource(wfile, bean, None)
        elif method == 'DELETE':
            doDeleteResource(wfile, bean, None)


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


def doGetResource(wfile, bean, view):
    RenderWeblibEdit(wfile).output(bean)


def doPutResource(wfile, bean, view):
    wlib = weblib.getMainBm()
    
    if not bean.validate():
        RenderWeblibEdit(wfile).output(bean)
        return
        
    if bean.newTags:
        assert bean.create_tags
        for t in bean.newTags:
            l = weblib.Tag(name=unicode(t))
            wlib.addTag(l)
        # reparse after created tags    
        bean._parseTags()
        assert not bean.newTags
        
    item = bean.item
    # is it an existing item?
    if bean.rid >= 0 and wlib.webpages.getById(bean.rid):
        # update existing item from bean
        item0             = wlib.webpages.getById(bean.rid)
        item0.name        = item.name       
        item0.url         = item.url        
        item0.description = item.description
        item0.tagIds      = item.tagIds   
        item0.relatedIds  = item.relatedIds 
        item0.modified    = item.modified   
        item0.lastused    = item.lastused   
        item0.cached      = item.cached     
        item = item0

    if item.id < 0:
        log.info('Adding WebPage %s' % unicode(item))
        wlib.addWebPage(item)
    else:    
        log.info('Updating WebPage %s' % unicode(item))
    
    wlib.fix()
    store.save(wlib)
    redirect(wfile, item.tags)


def doDeleteResource(wfile, bean, view):
    wlib = weblib.getMainBm()
    item = wlib.webpages.getById(bean.rid)
    if item:
        log.info('Deleting WebPage %s' % unicode(item))
        tags = item.tags      
        # todo: may need to delete tags too.    
        wlib.deleteWebPage(item)
        wlib.fix()
        store.save(wlib)  
    else:
        tags = []
            
    redirect(wfile, tags)


def queryWebLib(wfile, env, form, tag, querytxt):
    go_direct = form.getfirst('submit') == '>'
    if querytxt.lower().startswith('g '):
        querytxt = querytxt[2:]
        go_direct = True
    
    wlib = weblib.getMainBm()   

    tags, unknown = weblib.parseTags(wlib, tag)
    items, related, most_visited = weblib.query(wlib, querytxt, tags)

    if go_direct and most_visited:
        # quick jump
        wlib.visit(most_visited)
        redirect(wfile, '', url=most_visited.url)        
    else:
        folderNames = map(unicode, tags)
        currentCategory = tags and unicode(tags[-1]) or ''
        categoryList = []
        top_nodes = wlib.categories[1]
        for node in top_nodes:
            subcat = []
            categoryList.append((unicode(node[0]), subcat))
            for v, path in graph.dfsp(node):
                if len(path) < 3:
                    subcat.append(unicode(v))            
        RenderWeblib(wfile).output(env, querytxt, most_visited, folderNames, categoryList, currentCategory, items)
        


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


########################################################################

class RenderWeblib(response.ResponseTemplate):

    def __init__(self, wfile):
        super(RenderWeblib, self).__init__(wfile, 'weblib.html')

    """ weblib.html
    con:go_hint
            con:address
    rep:crumb
            con:link
    rep:catList
            con:link
            rep:catItem
                    con:link
    rep:webItemClass
            con:tag
            rep:webItem
                    con:edit
                    con:link
    """
    def render(self, node, env, querytxt, most_visited, folderNames, categoryList, currentCategory, webItemList):
        
        node.header.raw = response.getHeader(querytxt)
        
        if not most_visited:
            node.go_hint.omit()
        else:    
            node.go_hint.address.atts['href'] = make_go_url(most_visited)
            node.go_hint.address.content = most_visited.name
                    
        node.crumb.repeat(self.renderCrumb, folderNames)

        node.catList.repeat(self.renderCatItem, categoryList, currentCategory)

        node.webItemClass.repeat(self.renderWebItemClass, sorted(webItemList.items()))

        node.footer.raw = response.getFooter(env)

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


    def renderWebItemClass(self, node, category):
        tags, items = category
        tags = map(unicode,tags)
        node.tag.content = ', '.join(tags)
        node.webItem.repeat(self.renderWebItem, items)


    def renderWebItem(self, node, item):
        tags = ' (' + ','.join(map(unicode,item.tags)) + ')'
        if isinstance(item, weblib.Tag):
            node.link.content = item.name + tags
            node.edit.atts['href'] = '/%s/%s?view=edit' % (BASEURL, item.id)
        else:
            node.link.content = item.name + tags
            node.link.atts['href'] = make_go_url(item)
            node.edit.atts['href'] = '/%s/%s?view=edit' % (BASEURL, item.id)



class RenderWeblibEdit(response.ResponseTemplate):

    def __init__(self, wfile):
        super(RenderWeblibEdit, self).__init__(wfile, 'weblibEdit.html')

    """
        con:form
                con:id
                con:error
                        con:message
                con:name
                con:url
                con:description
                con:tags
                con:related
                con:modified_txt
                con:lastused_txt
                con:cached_txt
                con:modified
                con:lastused
                con:cached
        con:new_tags
    """

    def render(self, node, bean):

        node.header.raw = response.getHeader()

        item = bean.item
        wlib = weblib.getMainBm()

        form = node.form
        id = item.id == -1 and '_' or str(item.id)
        form.atts['action'] = '/%s/%s' % (BASEURL, id)

        if bean.errors:
            form.error.message.raw = '<br />'.join(bean.errors)
        else:
            form.error.omit()

        if item:
            form.id         .atts['value'] = unicode(item.id)
            form.name       .atts['value'] = item.name
            form.url        .atts['value'] = item.url
            form.description.content       = item.description
            form.tags       .atts['value'] = bean.tags
            form.related    .atts['value'] = bean.related
            form.modified   .atts['value'] = item.modified
            form.lastused   .atts['value'] = item.lastused
            form.cached     .atts['value'] = item.cached  
            
            if item.modified: 
                form.modified_txt.content = item.modified
            if item.lastused: 
                form.lastused_txt.content = item.lastused
            if item.cached:   
                form.cached_txt.content = item.cached  

        if bean.newTags:
            tags = u', '.join(bean.newTags)
            node.new_tags.content = "  new_tags = '%s';" % tags


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)