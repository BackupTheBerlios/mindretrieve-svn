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

log = logging.getLogger('cgi.tagFrm')


def _buildTags(req):
    """
    Build base_tag and form_tag. base_tag is the existing tag queried
    by tid. form_tag is a new tag instance build from parsing the form
    fields plus existing data.

    @return (base_tag, form_tag) or None if tid doesn't match any tag.
    """
    wlib = store.getWeblib()
    base_tag = wlib.tags.getById(req.tid)
    if not base_tag:
        return None
    if 'filled' in req.form:
        name = req.param('name') or ' '
        form_tag = weblib.Tag(
            id          = req.tid,
            name        = name,
            description = base_tag.description,
            flags       = base_tag.flags,
        )
        # HACK! Got around the empty string check in Tag.__init__
        if not req.param('name'):
            form_tag.name = ''
    else:
        form_tag = base_tag.__copy__()
    return base_tag, form_tag


def main(wfile, req):
    # this is called from the controller weblib
    tags = _buildTags(req)
    if not tags:
        wfile.write('404 not found\r\n\r\n@%s not found' % req.tid)
        return

    base_tag, form_tag = tags

    if req.method == 'POST':
        # we only do category_collapse setting right now
        if 'category_collapse' not in req.form:
            doPostResource(wfile, base_tag, form_tag)
        else:
            # category_collapse is special case
            doPostCategoryCollapse(wfile, req)
    elif req.method == 'DELETE':
        doDeleteResource(wfile, base_tag)
    else:
        doGetResource(wfile, form_tag)


def doGetResource(wfile, form_tag):
    FormRenderer(wfile).output([], form_tag)


def doPostResource(wfile, base_tag, form_tag):
    wlib = store.getWeblib()

    newName = form_tag.name.strip()
    if not newName:
        errors = ['Please enter a name']
        FormRenderer(wfile).output(errors, form_tag)
        return
    for c in weblib.Tag.ILLEGAL_CHARACTERS:
        if c in newName:
            errors = ['These characters are not allowed in tag name: ' + weblib.Tag.ILLEGAL_CHARACTERS]
            FormRenderer(wfile).output(errors, form_tag)
            return

    merge_tag = wlib.tags.getByName(newName)
    if merge_tag and merge_tag.id != base_tag.id:
        wlib.tag_merge_del(base_tag, merge_tag)     # merge with existing tag
        new_id = merge_tag.id
    else:
        wlib.tag_rename(base_tag, newName)          # just a rename (or change of capitalization)
        new_id = base_tag.id

    response.redirect(wfile, '/updateParent?url=' + urllib.quote('/weblib?tag=@%s' % new_id))


def doPostCategoryCollapse(wfile, req):
    wlib = store.getWeblib()

    flag = req.param('category_collapse').lower() == 'on'

    log.debug('setCategoryCollapse @%s %s' % (req.tid, flag))

    wlib.setCategoryCollapse(req.tid, flag)

    # response for debug only
    wfile.write('content-type: text/plain\r\n')
    wfile.write('cache-control: no-cache\r\n')
    wfile.write('\r\n')
    wfile.write('setCategoryCollapse @%s %s' % (req.tid, flag))


def doDeleteResource(wfile, base_tag):
    wlib = store.getWeblib()

    log.info('Deleting Tag %s' % unicode(base_tag))
    wlib.tag_merge_del(base_tag, None)

    response.redirect(wfile, '/updateParent?url=/weblib')


# ----------------------------------------------------------------------

class FormRenderer(response.CGIRenderer):
    TEMPLATE_FILE = 'weblibTagForm.html'
    """
    con:form
            con:error
                    con:message
            con:name
    """
    def render(self, node, errors, tag):
        wlib = store.getWeblib()

        form = node.form

        id = tag.id < 0 and '_' or str(tag.id)
        form.atts['action'] = '/weblib/@%s' % id

        if errors:
            form.error.message.raw = '<br />'.join(errors)
        else:
            form.error.omit()

        form.name.atts['value'] = tag.name


# weblibForm get invoked from CGI weblib.py

#if __name__ == "__main__":
#    main(sys.stdin, sys.stdout, os.environ)