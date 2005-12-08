import datetime
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

        # tags string as entered by user
        self.tags = ''

        # tags not known
        self.newTags = sets.Set()
        self.create_tags = req.param('create_tags')

        self.errors = []

        if req.method == 'GET':
            self._parse_GET(req)
        else:
            self._parse_PUT(req)


    def _parse_GET(self, req):
        """
        Parse submission from via bookmarklet or links
          method: GET
          parameters: url, title, description
        """
        wlib = store.getWeblib()

        # Three possiblities:
        #
        # 1. rid is an existing webpage
        #    The edit link from main page or
        #    user enter URL directly or
        #    request of case 3 redirected to an existing rid
        #
        # 2. rid is -1 and URL is not found in weblib
        #    Submit new page via bookmarklet
        #
        # 3. rid is -1 and URL is found in weblib
        #    Submit existing page via bookmarklet

        item = (req.rid > 0) and wlib.webpages.getById(req.rid) or None
        if item:
            # Case 1. make a copy of existing item
            item = item.__copy__()
            # overwritten with request parameters (only if defined)
            # usually only defined if it is redirected from case 3 request.
            if req.param('title')      : item.name        = req.param('title')
            if req.param('url')        : item.url         = req.param('url')
            if req.param('description'): item.description = req.param('description')
        else:
            url = req.param('url')
            matches = query_wlib.find_url(wlib, url)
            if not matches:
                # Case 2. this is a new webpage
                today = datetime.date.today().isoformat()
                item = weblib.WebPage(
                    name        = req.param('title'),
                    url         = url,
                    description = req.param('description'),
                    modified    = today,
                    lastused    = today,
                )

                if wlib.getDefaultTag():
                    item.tags = [wlib.getDefaultTag()]
            else:
                # Case 3. use existing webpage
                item = matches[0].__copy__()
                # however override with possibly new title and description
                item.name        = req.param('title')
                item.description = req.param('description')
                # actually the item is not very important because we
                # are going to redirect the request to the proper rid.

        self.item = item
        self.tags  = ', '.join([l.name for l in item.tags])


    def _parse_PUT(self, req):
        """
        Parse submission from form
          method: PUT
          parameters: description, title, url, tags, modified, lastused, cached
             (plus some more auxiliary parameters)
        """
        wlib = store.getWeblib()
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


    def _parseTags(self, req):
        """ Parse the 'tags' parameter. Check for exsiting and new tags. """
        wlib = store.getWeblib()
        self.tags = req.param('tags')
        self.item.tags, self.newTags = weblib.parseTags(wlib, self.tags)


    def validate(self):
        if not self.item.name:
            self.errors.append('Please enter a name.')
        if not self.item.url:
            self.errors.append('Please enter an address.')
        if self.newTags:
            # check for illegal characters first
            s = ''.join(self.newTags)
            for c in weblib.Tag.ILLEGAL_CHARACTERS:
                if c in s:
                    # found illegal characters
                    self.errors.append('These characters are not allowed in tag name: ' + weblib.Tag.ILLEGAL_CHARACTERS)
                    self.newTags = []
                    break
            else:
                # cleared for illegal characters check, create?
                if not self.create_tags:
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

    # if rid is defined, make sure it is valid
    if req.rid > 0:
        if not store.getWeblib().webpages.getById(req.rid):
            wfile.write('404 not found\r\n\r\nrid %s not found' % req.rid)

    if req.method == 'GET':
        bean = Bean(req)
        if req.rid == -1 and bean.item.id > 0:
            # if bookmarklet to an existing item, redirect to the appropiate rid
            url = '%s?%s' % (request.rid_url(bean.item.id), req.env.get('QUERY_STRING',''))
            response.redirect(wfile, url)
        else:
            doGetResource(wfile, req, bean)
    elif req.method == 'PUT':
        bean = Bean(req)
        doPutResource(wfile, req, bean)
    elif req.method == 'DELETE':
        doDeleteResource(wfile, req)


def doGetResource(wfile, req, bean):
    FormRenderer(wfile).output(bean)


def doPutResource(wfile, req, bean):
    wlib = store.getWeblib()

    if not bean.validate():
        FormRenderer(wfile).output(bean)
        return

    if bean.newTags:
        assert bean.create_tags
        for t in bean.newTags:
            l = weblib.Tag(name=unicode(t))
            store.getStore().writeTag(l)
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
        store.getStore().writeWebPage(item)
    else:
        log.info('Updating WebPage: %s' % unicode(item))
        store.getStore().writeWebPage(item)

    response.redirect(wfile, '/updateParent')


def doDeleteResource(wfile, req):
    wlib = store.getWeblib()
    item = wlib.webpages.getById(req.rid)
    if item:
        log.info('Deleting WebPage %s' % unicode(item))
        store.getStore().removeItem(item)

    response.redirect(wfile, '/updateParent')


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
        wlib = store.getWeblib()

        node.form_title.content = item.id == -1 and 'Add Entry' or 'Edit Entry'

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