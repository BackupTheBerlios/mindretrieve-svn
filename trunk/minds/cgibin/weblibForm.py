import logging
import os
import sets
import sys
import urllib

from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import store

log = logging.getLogger('cgi.weblib')


class Bean(object):
    """ The bean that represents one web entry """
    
    def __init__(self, rid, form):
        self.rid = rid
        self.form = form     
        self.item = None

        self.tags = ''
        self.related = ''
        
        # tags not known
        self.newTags = sets.Set()
        self.create_tags = self.form.getfirst('create_tags','').decode('utf-8')
        
        self.errors = []
        
        self._readForm(rid, form)


    def _readForm(self, rid, form):
        wlib = store.getMainBm()
        
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
                item.tags = [wlib.getDefaultTag()]
                item.tags = filter(None, item.tags) # don't want [None]
                
            self.item = item
            self.tags  = ', '.join([l.name for l in item.tags])
            self.related = ', '.join([l.name for l in item.related])
        

    def _parseTags(self):
        wlib = store.getMainBm()

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
        doDeleteResource(wfile, env, bean)


def doGetResource(wfile, env, bean):
    return_url = request.get_return_url(env, bean.form)
    EditRenderer(wfile,env,'').output( return_url, bean)


def doPutResource(wfile, env, bean):
    wlib = store.getMainBm()
    return_url = request.get_return_url(env, bean.form)
    
    if not bean.validate():
        EditRenderer(wfile,env,'').output( return_url, bean)
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
        item0.tags        = item.tags[:]
        item0.relatedIds  = item.relatedIds 
        item0.modified    = item.modified   
        item0.lastused    = item.lastused   
#        item0.cached      = item.cached     
        item = item0

    if item.id < 0:
        log.info('Adding WebPage: %s' % unicode(item))
        wlib.addWebPage(item)
    else:    
        log.info('Updating WebPage: %s' % unicode(item))
    
    wlib.categorize()
    store.save(wlib)
    response.redirect(wfile, return_url)


def doDeleteResource(wfile, env, bean):
    wlib = store.getMainBm()
    item = wlib.webpages.getById(bean.rid)
    if item:
        log.info('Deleting WebPage %s' % unicode(item))
        # todo: may need to delete tags too.    
        wlib.deleteWebPage(item)
        wlib.categorize()
        store.save(wlib)  
    return_url = request.get_return_url(env, bean.form)
    response.redirect(wfile, return_url)


# ----------------------------------------------------------------------

class EditRenderer(response.CGIRendererHeadnFoot):
    TEMPLATE_FILE = 'weblibForm.html'
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
    def render(self, node, return_url, bean):

        item = bean.item
        wlib = store.getMainBm()

        node.form_title.content = item.id == -1 and 'Add entry' or 'Edit entry'
        
        form = node.form
        id = item.id == -1 and '_' or str(item.id)
        form.atts['action'] = request.rid_url(id)

        if bean.errors:
            form.error.message.raw = '<br />'.join(bean.errors)
        else:
            form.error.omit()

        if item:
            form.return_url .atts['value'] = return_url
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

        tags = bean.newTags and u', '.join(bean.newTags) or ''
        ##TODO: encode tags for javascript in HTML
        node.form.new_tags.content = node.form.new_tags.content % tags 

if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)