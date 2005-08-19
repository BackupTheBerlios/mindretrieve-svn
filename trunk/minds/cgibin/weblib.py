#import codecs
import cgi
import datetime
import logging
import os, sys
import sets
import string
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
    """ The bean that represents one web entry """
    
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
        
    if action == 'organize':
        doOrganize(wfile, env, form)
        
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
            doGetResource(wfile, env, bean, None)
        elif method == 'PUT':
            doPutResource(wfile, env, bean, None)
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


def doGetResource(wfile, env, bean, view):
    EditRenderer(wfile,env,'').output(bean)


def doPutResource(wfile, env, bean, view):
    wlib = weblib.getMainBm()
    
    if not bean.validate():
        EditRenderer(wfile,env,'').output(bean)
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


def doOrganize(wfile, env, form):
    wlib = weblib.getMainBm()
##    wfile.write('content-type: text/plain\r\n\r\n')
    ## todo: when nothing selected?
    some_tags = sets.Set()##
    title=''##
    for k in form.keys():
        if not k .isdigit():
            continue
        item = wlib.webpages.getById(int(k))
        some_tags.union_update(item.tags)
        title = unicode(item)
##        wfile.write(unicode(item))
##        wfile.write('\n')
    some_tags = map(unicode,some_tags)
    EntryOrgRenderer(wfile, env, '').output(title,some_tags,some_tags)


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


########################################################################

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


class EditRenderer(response.CGIRendererHeadnFoot):
    TEMPLATE_FILE = 'weblibEdit.html'
    """
    con:header
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
    con:footer    
    """
    def render(self, node, bean):

        item = bean.item
        wlib = weblib.getMainBm()

        node.form_title.content = item.id == -1 and 'Add entry' or 'Edit entry'
        
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


class EntryOrgRenderer(response.CGIRendererHeadnFoot):
    TEMPLATE_FILE = 'weblibEntryOrg.html'
    """
    con:header
    con:form_title
    con:edit_form
            con:id_list
            con:error
                    con:message
            con:all_tags
            con:some_tags
    con:footer    
    """
    def render(self, node, title, all_tags, some_tags):
        t = string.Template(node.form_title.content)
        node.form_title.content = t.substitute(name=title)
        
        t = string.Template(node.edit_form.all_tags.content)
        node.edit_form.all_tags.content = t.safe_substitute(all_tags=u', '.join(all_tags))
        
        t = string.Template(node.edit_form.some_tags.content)
        node.edit_form.some_tags.content = t.safe_substitute(some_tags=u', '.join(some_tags))


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)