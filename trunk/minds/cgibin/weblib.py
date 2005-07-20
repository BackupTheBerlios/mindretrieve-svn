import codecs
import cgi
import datetime
import logging
import os, sys
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

bookmarkletFull = """
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
    d.location='http://localhost:8050/weblib/_?u='+escape(u)+'&t='+escape(t)+'&ds='+escape(ds);
"""

bookmarklet = "javascript:d=document;u=d.location;t=d.title;ds='';mt=d.getElementsByTagName('meta');for(i=0;i<mt.length;i++){ma=mt[i].attributes;na=ma['name'];if(na&&na.value.toLowerCase()=='description'){ds=ma['content'].value;}}d.location='http://localhost:8050/weblib/_?u='+escape(u)+'&t='+escape(t)+'&ds='+escape(ds);"



def main(rfile, wfile, env):

    method, rid, view, label, query, form = parseForm(rfile, env)

    log.debug('method %s rid %s view %s [action %s]', method, rid, view, form.getfirst('action','n/a'))

    if rid != None:

        if method == 'GET':
            doGetResource(wfile, form, rid, view)

        elif method == 'PUT':
            doPutResource(wfile, form, rid, view)

        elif method == 'DELETE':
            doDeleteResource(wfile, form, rid, view)

    else:
        queryWebLib(wfile, form, label, query)



def parseForm(rfile, env):

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

    method = env.get('REQUEST_METHOD','GET')

    # the edit form can only do GET, make it REST
    action = form.getfirst('action', '').lower()
    if action == 'ok':
        method = 'PUT'
    elif action == 'delete':
        method = 'DELETE'

    method = method.upper()

    view   = form.getfirst('view', '')
    label  = form.getfirst('label','')
    query  = form.getfirst('query','')

    return method, rid, view, label, query, form



def doGetResource(wfile, form, rid, view):
    wlib = weblib.getMainBm()
    item = wlib.id2entry.get(rid, None)
    if not item:
        item = wlib.newWebPage(
            name        = form.getfirst('t',''),
            url         = form.getfirst('u',''), 
            description = form.getfirst('ds',''),
        )
    RenderWeblibEdit(wfile).output(item)


def doPutResource(wfile, form, rid, view):
    wlib = weblib.getMainBm()
    item = wlib.id2entry.get(rid, weblib.WebPage())

    _labels = form.getfirst('labels','')
    item.labels, unknown = weblib.parseLabels(wlib, _labels)
    labelIds = [l.id for l in item.labels]

    _related = form.getfirst('related','')
    item.related, unknown = weblib.parseLabels(wlib, _related)
    relatedIds = [l.id for l in item.related]
    #TODO: unknown should be new labels

    item.name        = form.getfirst('t','')
    item.url         = form.getfirst('u','')
    item.description = form.getfirst('ds','')
    item.comment     = form.getfirst('comment','')
    item.labelIds    = labelIds
    item.relatedIds  = relatedIds
    item.modified    = form.getfirst('modified','')
    item.lastused    = form.getfirst('lastused','')
    item.cached      = form.getfirst('cached','')

    if item.id < 0:
        log.info('Adding WebPage %s' % unicode(item))
        wlib.addWebPage(item)
    else:    
        log.info('Updating WebPage %s' % unicode(item))
    
    wlib.fix()
    store.save(wlib)
    redirect(wfile, item.labels)


def doDeleteResource(wfile, form, rid, view):
    wlib = weblib.getMainBm()
    item = wlib.id2entry.get(rid, None)
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


def queryWebLib(wfile, form, label, query):

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

    RenderWeblib(wfile).output(folderNames, items, isTag, related)


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

    def render(self, node, folderNames, categoryList, isTag, isRelated):
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
        node.link.atts['href'] = '%s?%s' % (BASEURL, urllib.urlencode((('label',item),),True) )  ### BUG BUG unicode


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
                con:name
                con:url
                con:description
                con:comment
                con:labels
                con:modified
    """

    def render(self, node, item):

        wlib = weblib.getMainBm()

        form = node.form
        id = item.id == -1 and '_' or str(item.id)
        form.atts['action'] = '/%s/%s' % (BASEURL, id)

        if item:
            form.id         .atts['value'] = unicode(item.id)
            form.name       .atts['value'] = item.name
            form.url        .atts['value'] = item.url
            form.description.content       = item.description
            form.labels     .atts['value'] = ', '.join([l.name for l in item.labels])
            form.related    .atts['value'] = ', '.join([l.name for l in item.related])
            form.modified   .atts['value'] = item.modified
            form.lastused   .atts['value'] = item.lastused
            form.cached     .atts['value'] = item.cached  


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)