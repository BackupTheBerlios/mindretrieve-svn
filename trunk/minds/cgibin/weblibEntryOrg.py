import cgi
import itertools
import logging
import os
import sets
import string
import sys

from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import store

log = logging.getLogger('cgi.entryOrg')

SET, ADD_REMOVE = range(1,3)
OPTION_MAP = {
  'set_option': SET,
  'add_remove_option': ADD_REMOVE,
}

## todo: when nothing selected?
# /weblib.entryOrg?action=organize&271=on&132=on&157=on&203=on
# /weblib.entryOrg?method=POST&id_list=840&option=set_option&set_tags=tech&add_tags=&remove_tags=&action=OK&create_tags=

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

    wlib = store.getMainBm()
    entries = []
    for k in itertools.chain(req.form.keys(), id_list):
        k = k.strip()
        if not k.isdigit():
            continue
        item = wlib.webpages.getById(int(k))
        if item:
            entries.append(item)
    return entries


def doPost(wfile, req):
    wlib = store.getMainBm()
    entries = _buildEntries(req)
    errors = []

    # parse set/add/remove tags
    set_tags = ''
    add_tags = ''
    remove_tags = ''
    option = req.param('option')
    option = OPTION_MAP.get(option,None)
    if option == SET:
        set_tags = req.param('set_tags')
    elif option == ADD_REMOVE:
        add_tags = req.param('add_tags')
        remove_tags = req.param('remove_tags')
    else:
        errors.append('Please select set tags or add or remove tags.')
    set_tags, unknown1 = weblib.parseTags(wlib, set_tags)
    add_tags, unknown2 = weblib.parseTags(wlib, add_tags)
    remove_tags, unknown3 = weblib.parseTags(wlib, remove_tags)

    # deal with new tags
    create_tags = req.param('create_tags')
    unknown = []
    if (unknown1 or unknown2 or unknown3) and not create_tags:
        unknown = unknown1 + unknown2 + unknown3
        tags = u', '.join(unknown)
        errors.append('These tags are not previous used: ' + tags)

    if errors:
        doShowForm(wfile, req, errors, new_tags=unknown)
        return

    if unknown1:
        set_tags.extend(weblib.create_tags(wlib,unknown1))
    if unknown2:
        add_tags.extend(weblib.create_tags(wlib,unknown2))

    log.debug('organizeEntries %s entries set %s add %s remove %s.', len(entries), set_tags, add_tags, remove_tags)
    weblib.organizeEntries(entries, set_tags, add_tags, remove_tags)
    store.save(wlib)

    return_url = request.get_return_url(req)
    response.redirect(wfile, return_url)


def doDelete(wfile, req):
    wlib = store.getMainBm()
    entries = _buildEntries(req)
    for item in entries:
        try:
            log.debug('Delete web page: %s', unicode(item))
            wlib.deleteWebPage(item)
        except:
            log.exception('Unable to delete: %s', unicode(item))
    store.save(wlib)
    return_url = request.get_return_url(req)
    response.redirect(wfile, return_url)


def doShowForm(wfile, req, errors=None, new_tags=None):
    entries = _buildEntries(req)
    names = ''
    all_tags = []
    some_tags = sets.Set()
    for item in entries:
        if not names:
            names = unicode(item)
        if not all_tags:
            all_tags = sets.Set(item.tags)
        else:
            all_tags.intersection_update(item.tags)
        some_tags.union_update(item.tags)

    ids = [item.id for item in entries]
    some_tags.difference_update(all_tags)
    all_tags = map(unicode,all_tags)
    some_tags = map(unicode,some_tags)

    # refill if data entered for this form
    option = req.param('option')
    option = OPTION_MAP.get(option, None)
    set_tags = req.param('set_tags')
    add_tags = req.param('add_tags')
    remove_tags = req.param('remove_tags')

    return_url = request.get_return_url(req)
    EntryOrgRenderer(wfile, req.env, '').output(
        return_url,
        errors,
        new_tags,
        ids,
        names,
        all_tags,
        some_tags,
        option,
        set_tags,
        add_tags,
        remove_tags,
        )


# ----------------------------------------------------------------------

class EntryOrgRenderer(response.CGIRendererHeadnFoot):
    TEMPLATE_FILE = 'weblibEntryOrg.html'
    """ 2005-08-22
    con:header
    con:edit_form
            con:id_list
            con:error
                    con:message
            con:form_title
            con:all_tags
            con:some_tags
            con:set_option
            con:set_tags
            con:add_remove_option
            con:add_tags
            con:remove_tags
            con:new_tags_var
    con:footer
    """
    def render(self, node, return_url, errors, new_tags, ids, names, all_tags, some_tags, option, set_tags, add_tags, remove_tags):
        node.edit_form.return_url .atts['value'] = return_url
        node.edit_form.id_list.atts['value'] = ','.join(map(str,ids))

        if errors:
            node.edit_form.error.message.raw = '<br />'.join(errors)
        else:
            node.edit_form.error.omit()

        t = string.Template(node.edit_form.form_title.content)
        node.edit_form.form_title.content = t.substitute(total=len(ids), names=names, )

        t = string.Template(node.edit_form.all_tags.content)
        node.edit_form.all_tags.content = t.safe_substitute(all_tags=u', '.join(all_tags))

        t = string.Template(node.edit_form.some_tags.content)
        node.edit_form.some_tags.content = t.safe_substitute(some_tags=u', '.join(some_tags))

        if option == SET:
            node.edit_form.set_option.atts['checked'] = '1'
        elif option == ADD_REMOVE:
            node.edit_form.add_remove_option.atts['checked'] = '1'
        if set_tags:
            node.edit_form.set_tags.atts['value'] = set_tags
        if add_tags:
            node.edit_form.add_tags.atts['value'] = add_tags
        if remove_tags:
            node.edit_form.remove_tags.atts['value'] = remove_tags

        tags = new_tags and u', '.join(new_tags) or ''
        # TODO: need to escape tags for javascript;
        node.edit_form.new_tags_var.content = node.edit_form.new_tags_var.content % tags


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)
