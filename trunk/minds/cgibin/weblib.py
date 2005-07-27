import codecs
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

log = logging.getLogger('cgi.weblib')

BASEURL = 'weblib'


"""
weblib                      show home page

weblib?label=xx,yy          show label

weblib/_                    show edit screen        PUT weblib/_
weblib/%id                                          PUT weblib/%id            
                                                    redirect weblib?label=xx,yy    
    view=?
    field=?                   
                                                             
                                                    DELETE weblib/%id
                                                    redirect weblib?label=xx,yy    

weblib/%id/cache
weblib/%id/cache&cid=

weblib?query=xx             ?    
"""

BOOKMARKLET = """
javascript:
    d=document;
    u=d.location;
    t=d.title;
    ds='';
    mt=d.getElementsByTagName('meta');
    for(i=0;i<mt.length;i++){
        ma=mt[i].attributes;
        na=ma['name'];
        if(na&&na.value.toLowerCase()=='description'){
            ds=ma['content'].value;
        }
    }
    d.location='http://%s/weblib/_?u='+escape(u)+'&t='+escape(t)+'&ds='+escape(ds);
"""

def getBookmarklet(hostname):
    s = BOOKMARKLET % hostname
    s = s.replace('\n','').replace(' ','') # compress the spaces
    return s


class Bean(object):
    
    def __init__(self, rid, form):
        self.rid = rid
        self.form = form     
        self.item = None

        # tags string. This is tentative and may contain new tags.
        self.labels = ''
        self.related = ''
        
        # tags not known
        self.newTags = sets.Set()
        
        self.errors = []
        
        self._readForm(rid, form)


    def _readForm(self, rid, form):
        wlib = weblib.getMainBm()
        
        if form.has_key('filled'):
            item = weblib.WebPage(
                id          = rid,
                name        = form.getfirst('t',''),
                url         = form.getfirst('u',''),
                description = form.getfirst('ds',''),
                modified    = form.getfirst('modified',''),
                lastused    = form.getfirst('lastused',''),
                cached      = form.getfirst('cached',''),
            )

            _labels = form.getfirst('labels','')
            item.labels, unknown_labels = weblib.parseLabels(wlib, _labels)
            item.labelIds = [l.id for l in item.labels]

            _related = form.getfirst('related','')
            item.related, unknown_related = weblib.parseLabels(wlib, _related)
            item.relatedIds = [l.id for l in item.related]
            
            self.item = item
            self.labels = _labels
            self.related = _related
            self.newTags.union_update(unknown_labels)
            self.newTags.union_update(unknown_related)

        else:    
            item = wlib.id2entry.get(rid, None)
            if item:
                # make a copy of existing item    
                item = item.__copy__()
            else:    
                item = wlib.newWebPage(
                    name        = form.getfirst('t',''),
                    url         = form.getfirst('u',''),
                    description = form.getfirst('ds',''),
                )
                
            self.item = item
            self.labels  = ', '.join([l.name for l in item.labels])
            self.related = ', '.join([l.name for l in item.related])
        
    
    def validate(self):
        if not self.item.name:
            self.errors.append('Please enter a name.')    
        if not self.item.url:
            self.errors.append('Please enter an address.')    
        if self.newTags:
            tags = u', '.join(self.newTags)
            self.errors.append('These tags are not previous used: ' + tags)                
        return not self.errors


    def __str__(self):
        if not self.item: 
            return 'None'
        else:        
            return u'%s(%s)' % (self.item.name, self.item.rid)

    
def main(rfile, wfile, env):

    method, rid, label, view, query, form = parseURL(rfile, env)

    log.debug('method %s rid %s view %s [action %s]', method, rid, view, form.getfirst('action','n/a'))

    if rid == None:
        queryWebLib(wfile, env, label, query)
        
    else:    
        # build bean from rid and other form parameters
        bean = Bean(rid, form)
        if method == 'GET':
            doGetResource(wfile, bean, view)
        elif method == 'PUT':
            doPutResource(wfile, bean, view)
        elif method == 'DELETE':
            doDeleteResource(wfile, bean, view)


def parseURL(rfile, env):
    """ 
    @return method, rid, label, view, query, form
        method - 'GET', 'PUT', 'DELETE' 
        rid - None: n/a; '_': new item; int: resource id                
        label - string of comma seperated tags
        view - view parameter ('XML', '', etc. ???)
        query - query parameter (2005-07-25 unused?)
        form - cgi.FieldStorage
    """  

    form = cgi.FieldStorage(fp=rfile, environ=env)

    # parse resource id (None, -1, int)
    resource = env.get('PATH_INFO', '').strip('/')
    rid = None
    if resource == '_':
        rid = -1
    else:
        try:
            rid = int(resource)
        except ValueError: pass

    # the edit form can only do GET, use 'action' as an alternative
    method = env.get('REQUEST_METHOD','GET')
    action = form.getfirst('action', '').lower()
    if action == 'ok':
        method = 'PUT'
    elif action == 'delete':
        method = 'DELETE'
    method = method.upper()

    # other parameters
    label  = form.getfirst('label','')
    view   = form.getfirst('view', '')
    query  = form.getfirst('query','')

    return method, rid, label, view, query, form



def doGetResource(wfile, bean, view):
    RenderWeblibEdit(wfile).output(bean)



def doPutResource(wfile, bean, view):
    wlib = weblib.getMainBm()
    
    if not bean.validate():
        RenderWeblibEdit(wfile).output(bean)
        return
        
    item = bean.item
    # is it an existing item?
    if bean.rid >= 0 and wlib.id2entry.has_key(bean.rid):
        # update existing item from bean
        item0 = wlib.id2entry[bean.rid]
        item0.name        = item.name       
        item0.url         = item.url        
        item0.description = item.description
        item0.labelIds    = item.labelIds   
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
    redirect(wfile, item.labels)


def doDeleteResource(wfile, bean, view):
    wlib = weblib.getMainBm()
    item = wlib.id2entry.get(bean.rid, None)
    if item:
        log.info('Deleting WebPage %s' % unicode(item))
        labels = item.labels      
        # todo: may need to delete labels too.    
        wlib.deleteWebPage(item)
        wlib.fix()
        store.save(wlib)  
    else:
        labels = []
            
    redirect(wfile, labels)



def queryWebLib(wfile, env, label, query):
    # generates the bookmarklet
    host = env.get('SERVER_NAME','')
    port = env.get('SERVER_PORT','80')
    # SERVER_NAME is actually not that good. Override with 'localhost'
    host = 'localhost'  
    bookmarklet = getBookmarklet('%s:%s' %  (host, port))
    
    wlib = weblib.getMainBm()

    labels, unknown = weblib.parseLabels(wlib, label)
    if labels:
        items, related = weblib.query(wlib, labels)
    else:    
        items, related = weblib.queryMain(wlib)

    isTag = []
    for label in labels:
        isTag = label.isTag

    folderNames = map(unicode, labels)

    RenderWeblib(wfile).output(folderNames, items, isTag, related, bookmarklet)



def redirect(wfile, labels):
    if labels: 
        qs = u','.join(map(unicode, labels))
        qs = qs.encode('utf8')
        qs = '?label=' + urllib.quote_plus(qs)
        wfile.write('location: ' + '/%s%s\r\n\r\n' % (BASEURL, qs))
    else:
        wfile.write('location: ' + '/%s\r\n\r\n' % (BASEURL,))



########################################################################

class RenderWeblib(response.ResponseTemplate):

    def __init__(self, wfile):
        super(RenderWeblib, self).__init__(wfile, 'weblib.html')

    """ weblib.html
    tem:
	con:tagList
		rep:tagItem
			con:link
	con:mainTag
	rep:category
		con:tag
		rep:bookmark
			con:link
			con:edit
    """

    def render(self, node, folderNames, categoryList, isTag, isRelated, bookmarklet):
        node.bookmarklet.atts['href'] = bookmarklet.replace("'",'&apos;')
        
        mainTag = u','.join(folderNames)

        tags = list(isTag) + list(isRelated)
        tags = weblib.sortLabels(tags)
        tags = map(unicode,tags)

        node.tagList.content = mainTag
        node.tagList.tagItem.repeat(self.renderTagItem, tags)

        node.mainTag.content = mainTag
        node.category.repeat(self.renderCategory, sorted(categoryList.items()))


    def renderTagItem(self, node, item):
        node.link.content = item
        node.link.atts['href'] = '%s?%s' % (BASEURL, urllib.urlencode((('label',item),),True) )  ### TODO: BUG BUG unicode


    def renderCategory(self, node, category):
        wlib = weblib.getMainBm()
        labels, items = category
        tags = map(unicode,labels)
        node.tag.content = ', '.join(tags)
        node.bookmark.repeat(self.renderWebPage, items)


    def renderWebPage(self, node, item):

        wlib = weblib.getMainBm()
        labels = ' (' + ','.join(map(unicode,item.labels)) + ')'

        if isinstance(item, weblib.Label):
            node.link.content = item.name + labels
            node.edit.atts['href'] = '/%s/%s?view=edit' % (BASEURL, item.id)
        else:
            node.link.content = item.name + labels
            node.link.atts['href'] = item.url
            node.edit.atts['href'] = '/%s/%s?view=edit' % (BASEURL, item.id)



class RenderWeblibEdit(response.ResponseTemplate):

    def __init__(self, wfile):
        super(RenderWeblibEdit, self).__init__(wfile, 'weblibEdit.html')

    """
    tem:
        con:form
                con:id
                con:error
                        con:message
                con:name
                con:url
                con:description
                con:labels
                con:related
                con:modified
                con:lastused
                con:cached    
    """

    def render(self, node, bean):

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
            form.labels     .atts['value'] = bean.labels
            form.related    .atts['value'] = bean.related
            form.modified   .atts['value'] = item.modified
            form.lastused   .atts['value'] = item.lastused
            form.cached     .atts['value'] = item.cached  


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)