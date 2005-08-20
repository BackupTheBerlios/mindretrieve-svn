import cgi
#import datetime
import logging
import os
import sets
#import string
import sys
import urllib

from minds.config import cfg
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import store

log = logging.getLogger('cgi.weblib')

BASEURL = 'weblib'


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

    
def main(rfile, wfile, env, method, form, rid):
    # this is called from the controller weblib
    bean = Bean(rid, form)
    if method == 'GET':
        doGetResource(wfile, env, bean)
    elif method == 'PUT':
        doPutResource(wfile, env, bean)
    elif method == 'DELETE':
        doDeleteResource(wfile, bean)


def doGetResource(wfile, env, bean):
    EditRenderer(wfile,env,'').output(bean)


def doPutResource(wfile, env, bean):
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
    redirect_tags(wfile, item.tags)


def doDeleteResource(wfile, bean):
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
    redirect_tags(wfile, tags)


def redirect_tags(wfile, tags):
    if tags:
        if hasattr(tags,'encode'):##??
            qs = unicode(tags)    
        else:
            qs = u','.join(map(unicode, tags))
        qs = urllib.quote_plus(qs.encode('utf8'))
        url = '/%s?tag=%s' % (BASEURL, qs)
    else:
        url = '/%s' % BASEURL    
    wfile.write('location: %s\r\n\r\n' % url)



# ----------------------------------------------------------------------

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


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)