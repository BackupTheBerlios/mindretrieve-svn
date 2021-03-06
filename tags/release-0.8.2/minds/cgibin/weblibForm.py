import datetime
import logging
import os
import sets
import sys
import urllib
import urlparse
from xml.sax import saxutils

from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import query_wlib
from minds.weblib import store
from minds.weblib import util as weblib_util
from minds.weblib.win32 import ntfs_util

log = logging.getLogger('cgi.wlibFm')


def main(wfile, req):
    # this is called from the controller weblib

    # if rid is defined, make sure it is valid
    if req.rid > 0:
        if not store.getWeblib().webpages.getById(req.rid):
            wfile.write('404 not found\r\n\r\n')
            wfile.write('rid %s not found' % req.rid)

    if req.method == 'PUT':
        bean = Bean(req)
        doPutResource(wfile, req, bean)

    elif req.method == 'POST':
        wfile.write('404 Method Not Allowed\r\n\r\n')
        wfile.write('Use PUT to update the item.')

    elif req.method == 'DELETE':
        doDeleteResource(wfile, req)

    else: # otherwise it is GET
        bean = Bean(req)
        if req.rid == -1 and bean.oldItem:
            # if bookmarklet to an existing item, redirect to the appropiate rid
            url = '%s?%s' % (request.rid_url(bean.item.id), req.env.get('QUERY_STRING',''))
            response.redirect(wfile, url)

        else:
            doGetResource(wfile, req, bean)


class Bean(object):
    """ The bean that represents the state of the form """

    def __init__(self, req):

        self.item = None
        if req.rid > 0:
            # Could get None. But then there was a 404 check prior to this.
            self.oldItem = store.getWeblib().webpages.getById(req.rid)
        else:
            self.oldItem = None

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

        if self.oldItem:
            # Case 1. make a copy of the existing item
            item = self.oldItem.__copy__()
            # overwritten with request parameters (only if defined)
            # usually only defined if it is redirected from case 3 request.
#            if req.param('title')      : item.name        = req.param('title')
#            if req.param('url')        : item.url         = req.param('url')
#            if req.param('description'): item.description = req.param('description')
        else:
            url = req.param('url')
            matches = query_wlib.find_url(wlib, url)
            if not matches:
                # Case 2. this is a new webpage
                today = datetime.date.today().isoformat()
                if weblib_util.isFileURL(url):
                    item, tags = ntfs_util.makeWebPage(url)
                else:
                    item = weblib.WebPage(
                        name        = req.param('title'),
                        url         = url,
                        description = req.param('description'),
                        created     = today,
                        modified    = today,
                        lastused    = today,
                    )

                if wlib.getDefaultTag():
                    item.tags = [wlib.getDefaultTag()]
            else:
                # Case 3. use existing webpage
                self.oldItem = matches[0]
                item = self.oldItem.__copy__()
                # however override with possibly new title and description
                item.name        = req.param('title')
                item.description = req.param('description')
                # actually the item is not very important because we
                # are going to redirect the request to the proper rid.

        self.item = item
        # construct tags_description for editing
        self.item.tags_description  = ', '.join([l.name for l in item.tags])


    def _parse_PUT(self, req):
        """
        Parse submission from form
          method: PUT
          parameters: description, title, url, tags, created, modified, lastused
             (plus some more auxiliary parameters?)
        """
        wlib = store.getWeblib()
        if self.oldItem:
            # Update an existing item
            # Selectively update the field if parameter is supplied.
            # That way an API call can send a subset of parameters.
            self.item = self.oldItem.__copy__()
            if 'title'       in req.form: self.item.name         = req.param('title')
            if 'url'         in req.form: self.item.url          = req.param('url')
            if 'description' in req.form: self.item.description  = req.param('description')
            if 'created'     in req.form: self.item.created      = req.param('created')
            if 'modified'    in req.form: self.item.modified     = req.param('modified')
            if 'lastused'    in req.form: self.item.lastused     = req.param('lastused')
            if 'tags'        in req.form: self._parseTags(req)
        else:
            # create new item
            self.item = weblib.WebPage(
                name        = req.param('title'),
                url         = req.param('url'),
                description = req.param('description'),
                created     = req.param('created'),
                modified    = req.param('modified'),
                lastused    = req.param('lastused'),
            )
            self._parseTags(req)


    def _parseTags(self, req):
        """ Parse the 'tags' parameter. Check for exsiting and new tags. """
        wlib = store.getWeblib()
        tags_description = req.param('tags')
        self.item.tags, self.newTags = weblib.parseTags(wlib, tags_description)
        self.item.tags_description = tags_description


    def validate(self):
        if not self.item.name:
            self.errors.append('Please enter a name.')

        if not self.item.url:
            self.errors.append('Please enter an address.')

        if self.newTags:
            if weblib.Tag.hasIllegalChar(''.join(self.newTags)):
                self.errors.append('These characters are not allowed in tag name: ' + weblib.Tag.ILLEGAL_CHARACTERS)
                self.newTags = []
            else:
                if not self.create_tags:
                    tags = u', '.join(self.newTags)
                    self.errors.append('These tags are not previous used: ' + tags)

        return not self.errors


    def __str__(self):
        if not self.item:
            return 'None'
        else:
            return u'%s(%s)' % (self.item.name, self.item.id)


def doGetResource(wfile, req, bean):
    FormRenderer(wfile).output(bean)


def doPutResource(wfile, req, bean):
    wlib = store.getWeblib()

    if not bean.validate():
        FormRenderer(wfile).output(bean)
        return

    item = bean.item
    if bean.newTags:
        assert bean.create_tags
        item.tags = weblib.makeTags(store.getStore(), item.tags_description)

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
    """ 2005-12-09
    con:form_title
    con:form
            con:error
                    con:message
            con:name
            con:url
            con:url_link
            con:description
            con:tags
            con:created_txt
            con:modified_txt
            con:lastused_txt
            con:created
            con:modified
            con:lastused
            con:new_tags_js_var
    """
    def render(self, node, bean):

        item = bean.item
        wlib = store.getWeblib()

        if item.id == -1:
            node.form_title.content %= 'Add Entry'
            node.edit_header.omit()
        else:
            node.form_title.content %= 'Edit Entry'
            node.add_header.omit()

        form = node.form
        id = item.id < 0 and '_' or str(item.id)
        form.atts['action'] = request.rid_url(id)

        if bean.errors:
            escaped_errors = map(saxutils.escape, bean.errors)
            form.error.message.raw = '<br />'.join(escaped_errors)
        else:
            form.error.omit()

        if item:
            form.name       .atts['value'] = item.name
            form.url        .atts['value'] = item.url
            if weblib_util.isFileURL(item.url):
                scheme, netloc, url_path, _, _, _ = urlparse.urlparse(item.url)
                pathname = weblib_util.nt_url2pathname(url_path)
                form.url_link.atts['href']  = '/weblib/%s/url#%s' % (item.id, item.url)
                form.filename.content = pathname
            else:
                form.url_link.atts['href']  = item.url
                form.filename.omit()

            form.description.content       = item.description
            form.tags       .atts['value'] = bean.item.tags_description
            form.created    .atts['value'] = item.created

            if item.modified:
                form.modified_txt.content = item.modified
            if item.fetched:
                form.snapshot_txt.content = item.fetched

        tags = bean.newTags and u', '.join(bean.newTags) or ''
        encoded_tags = response.jsEscapeString(tags)
        node.form.new_tags_js_var.raw = node.form.new_tags_js_var.raw % encoded_tags

# weblibForm get invoked from CGI weblib.py

#if __name__ == "__main__":
#    main(sys.stdin, sys.stdout, os.environ)