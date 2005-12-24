import itertools
import logging
import os
import re
import sets
import sys
import urllib
from xml.sax import saxutils

from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import query_wlib
from minds.weblib import store

log = logging.getLogger('cgi.wlibfrm')


## todo: when nothing selected?

# /weblib/multiform?action=organize&271=on&132=on&157=on&203=on
# /weblib/multiform?method=POST&id_list=840&option=set_option&set_tags=tech&add_tags=&remove_tags=&action=OK&create_tags=

TAG_DELETE, TAG_UNCHANGE, TAG_SELECT = range(1,4)


def main(rfile, wfile, env):
    req = request.Request(rfile, env)
    if req.method == 'GET':
        doShowForm(wfile, req)
    elif req.method == 'POST':
        doPost(wfile, req)
    elif req.method == 'DELETE':
        doDelete(wfile, req)


def _buildEntries(req):
    # scan for ddd=On from 'checkbox' fields or id_list='ddd,ddd' from 'hidden' field
    # build the id list ids.
    id_list = req.param('id_list').split(',')

    wlib = store.getWeblib()

    entries = []
    for k in itertools.chain(req.form.keys(), id_list):
        k = k.strip()
        if not k.isdigit():
            continue
        item = wlib.webpages.getById(int(k))
        if item:
            entries.append(item)

    return entries


def _buildChecklist(req):
    """ @return list of (tag, value) """
    wlib = store.getWeblib()
    checklist = []          # list of (tag, flag)
    p = re.compile('\@\d+changed')
    for changed_key in req.form:
        if not p.match(changed_key):
            continue
        if not req.param(changed_key):
            continue
        key = changed_key[:-len('changed')]   # strip 'changed' to get @id
        try:
            id = int(key[1:])
        except:
            continue
        tag = wlib.tags.getById(id)
        if not tag:
            continue
        flag = bool(req.param(key))
        checklist.append((tag,flag))

    return checklist


def doShowForm(wfile, req, errors=[], checklist=[], new_tags=[]):
    entries = _buildEntries(req)

    # build ids, names
    ids = [item.id for item in entries]
    names = [unicode(item) for item in entries[:3]]
    if len(entries) > 3:
        names.append('...')

    # TODO BUG: below will fail if there is no entries

    # build all_tags, some_tags
    all_tags = None
    some_tags = sets.Set()
    for item in entries:
        if all_tags == None:
            # only instantiate this the first time
            all_tags = sets.Set(item.tags)
        else:
            all_tags.intersection_update(item.tags)
        some_tags.union_update(item.tags)

    some_tags.difference_update(all_tags)
    tags = [(tag.name, tag.id, TAG_SELECT, False) for tag in all_tags] + \
           [(tag.name, tag.id, TAG_UNCHANGE, False) for tag in some_tags]
    tags.sort()
    tags = [[id, name, flag, changed] for name, id, flag, changed in tags]

    # restore checkbox state from previous page
    for tag, flag in checklist:
        for tagItem in tags:
            if tagItem[0] == tag.id:
                # make flag either TAG_SELECT or TAG_DELETE
                tagItem[2] = flag and TAG_SELECT or TAG_DELETE
                tagItem[3] = True

    # refill if data entered for this form
    add_tags = req.param('add_tags')

    MultiFormRenderer(wfile).output(
        errors,
        new_tags,
        ids,
        names,
        tags,
        add_tags,
        )


def doPost(wfile, req):
    wlib = store.getWeblib()
    entries = _buildEntries(req)
    checklist = _buildChecklist(req)
    errors = []

    # parse add tags
    tags_description = req.param('add_tags')
    if weblib.Tag.hasIllegalChar(tags_description.replace(',',' ')):
        errors.append('These characters are not allowed in tag name: ' + weblib.Tag.ILLEGAL_CHARACTERS)
        tags_description = ''

    # check for new tags and the create_tags flag
    _, unknown = weblib.parseTags(wlib, tags_description)
    if unknown and (not req.param('create_tags')):
        tags = u', '.join(unknown)
        errors.append('These tags are not previous used: ' + tags)
        tags_description = ''

    # note: validation should be done, new tags will be created here
    set_tags = weblib.makeTags(store.getStore(), tags_description)
    remove_tags = []

    # going through checklist, add to set_tags, delete_tags
    for tag, flag in checklist:
        if flag:
            if tag not in set_tags:
                set_tags.append(tag)
        else:
            remove_tags.append(tag)

    if errors:
        doShowForm(wfile, req, errors, checklist=checklist, new_tags=unknown)
        return

    log.debug('EditTags for %s entries set(%s) remove(%s).', len(entries), set_tags, remove_tags)
    wlib.editTags(entries, [], set_tags, remove_tags)

    response.redirect(wfile, '/updateParent')


def doDelete(wfile, req):
    wlib = store.getWeblib()
    entries = _buildEntries(req)
    for item in entries:
        try:
            log.debug('Delete web page: %s', unicode(item))
            store.getStore().removeItem(item)
        except:
            log.exception('Unable to delete: %s', unicode(item))
    response.redirect(wfile, '/updateParent')


# ----------------------------------------------------------------------

class MultiFormRenderer(response.CGIRenderer):
    TEMPLATE_FILE = 'weblibMultiForm.html'
    """ 2005-12-09
    con:form
        con:id_list
        con:error
                con:message
        rep:title
        rep:tag
                con:checkbox
                con:hidden
                con:tagName
        con:add_tags
        con:new_tags_js_var
    """
    def render(self, node, errors, new_tags, ids, names, tags, add_tags=''):
        """
        @param tags - list of (id, name, flag, changed)
        """

        form = node.form
        if errors:
            escaped_errors = map(saxutils.escape, errors)
            form.error.message.raw = '<br />'.join(escaped_errors)
        else:
            form.error.omit()

        form.id_list.atts['value'] = ','.join(map(str,ids))

        form.title.repeat(self.renderTitle, names)

        form.tag.repeat(self.renderTag, tags)

        form.add_tags.atts['value'] = add_tags

        tags = new_tags and u', '.join(new_tags) or ''
        encode_tags = response.jsEscapeString(tags)
        node.form.new_tags_js_var.raw = node.form.new_tags_js_var.raw % encode_tags


    def renderTitle(self, node, title):
        node.content = title


    def renderTag(self, node, item):
        id, tag, flag, changed = item
        node.checkbox.atts['name'] = '@%s' % id
        node.hidden.atts['id']     = node.hidden.atts['id'] % id
        node.hidden.atts['name']   = node.hidden.atts['name'] % id
        node.tagName.content = tag

        # set/restore the checked and changed state
        node.atts['class'] = (flag == TAG_UNCHANGE) and 'tagUnchange' or 'tagChange'
        if flag == TAG_DELETE:
            del node.checkbox.atts['checked']
        if changed:
            node.hidden.atts['value'] = '1'


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)