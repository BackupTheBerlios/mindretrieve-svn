import logging
import os
import sets
import sys
import urllib

from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import query_wlib
from minds.weblib import store

log = logging.getLogger('cgi.wlibfrm')


class Bean(object):
    """ The bean that represents one web entry """

    def __init__(self, req):
        self.item = None

        # tags input as entered by user
        self.tags = ''

        # tags not known
        self.newTags = sets.Set()
        self.create_tags = req.param('create_tags')

        self.errors = []

        self._readForm(req)


    def _readForm(self, req):
        wlib = store.getMainBm()

        if 'filled' in req.form:
            # User is submitting form, use the parameters in the query
            self.item = weblib.WebPage(
                id          = req.rid,
                name        = req.param('title'),
                url         = req.param('url'),
                description = req.param('description'),
                modified    = req.param('modified'),
                lastused    = req.param('lastused'),
                cached      = req.param('cached'),
            )
            self._parseTags(req)

        else:
            # Request comes from three possible sources
            #
            # 1. The edit link from main page (or similar)
            #       rid is an existing webpage
            # 2. Submit new page via bookmarklet
            #       rid is -1 and URL is new
            # 3. Submit existing page via bookmarklet
            #       rid is -1 and URL found in weblib
            item = wlib.webpages.getById(req.rid)
            if item:
                # Case 1. make a copy of existing item
                item = item.__copy__()
            else:
                url = req.param('url')
                matches = query_wlib.find_url(wlib, url)
                if not matches:
                    # Case 2. this is a new webpage
                    item = wlib.newWebPage(
                        name        = req.param('title'),
                        url         = url,
                        description = req.param('description'),
                    )
                    if wlib.getDefaultTag():
                        item.tags = [wlib.getDefaultTag()]
                else:
                    # Case 3. use existing webpage
                    item = matches[0].__copy__()
                    # however override with possibly new title and description
                    item.name        = req.param('title')
                    item.description = req.param('description')
                    # note: subsequent action is POSTed to existing item's rid

            self.item = item
            self.tags  = ', '.join([l.name for l in item.tags])


    def _parseTags(self, req):
        wlib = store.getMainBm()
        self.tags = req.param('tags')
        self.item.tags, self.newTags = weblib.parseTags(wlib, self.tags)


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
            return u'%s(%s)' % (self.item.name, self.item.id)


def main(wfile, req):
    # this is called from the controller weblib
    bean = Bean(req)
    if req.method == 'GET':
        doGetResource(wfile, req, bean)
    elif req.method == 'PUT':
        doPutResource(wfile, req, bean)
    elif req.method == 'DELETE':
        doDeleteResource(wfile, req)


def doGetResource(wfile, req, bean):
    FormRenderer(wfile).output(bean)


def doPutResource(wfile, req, bean):
    wlib = store.getMainBm()

    if not bean.validate():
        FormRenderer(wfile).output(bean)
        return

    if bean.newTags:
        assert bean.create_tags
        for t in bean.newTags:
            l = weblib.Tag(name=unicode(t))
            wlib.addTag(l)
        # reparse after created tags
        bean._parseTags(req)
        assert not bean.newTags

    item = bean.item
    # is it an existing item?
    if item.id >= 0 and wlib.webpages.getById(item.id):
        # update existing item from bean
        item0             = wlib.webpages.getById(item.id)
        item0.name        = item.name
        item0.url         = item.url
        item0.description = item.description
        item0.tags        = item.tags[:]
        item0.modified    = item.modified
        item0.lastused    = item.lastused
#        item0.cached      = item.cached
        item = item0

    if item.id < 0:
        log.info('Adding WebPage: %s' % unicode(item))
        wlib.addWebPage(item)
        wlib.updateWebPage(item)
    else:
        wlib.updateWebPage(item)
        log.info('Updating WebPage: %s' % unicode(item))

    wlib.category.compile()
    store.save(wlib)

    response.redirect(wfile, '/updateParent.html')


def doDeleteResource(wfile, req):
    wlib = store.getMainBm()
    item = wlib.webpages.getById(req.rid)
    if item:
        log.info('Deleting WebPage %s' % unicode(item))
        wlib.deleteWebPage(item)
        wlib.category.compile()
        store.save(wlib)

    response.redirect(wfile, '/updateParent.html')


# ----------------------------------------------------------------------

class FormRenderer(response.CGIRenderer):
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
        wlib = store.getMainBm()

#        node.form_title.content = item.id == -1 and 'Add entry' or 'Edit entry'

        form = node.form
        id = item.id < 0 and '_' or str(item.id)
        form.atts['action'] = request.rid_url(id)

        if bean.errors:
            form.error.message.raw = '<br />'.join(bean.errors)
        else:
            form.error.omit()

        if item:
            form.name       .atts['value'] = item.name
            form.url        .atts['value'] = item.url
            form.url_link   .atts['href']  = item.url
            form.description.content       = item.description
            form.tags       .atts['value'] = bean.tags
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

# weblibForm get invoked from CGI weblib.py

#if __name__ == "__main__":
#    main(sys.stdin, sys.stdout, os.environ)