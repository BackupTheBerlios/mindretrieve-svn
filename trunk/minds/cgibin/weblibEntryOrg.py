import cgi
import itertools
import logging
import os
import sets
import string
import sys

from minds.config import cfg
from minds.cgibin.util import response
from minds import weblib

log = logging.getLogger('cgi.weblib')

BASEURL = 'weblib'

## todo: when nothing selected?
# http://localhost:8052/weblib.entryOrg?action=organize&271=on&132=on&157=on&203=on

def parseURL(rfile, env):
    form = cgi.FieldStorage(fp=rfile, environ=env)
    method = env.get('REQUEST_METHOD','GET').upper()
    return method, form


def main(rfile, wfile, env):

    method, form = parseURL(rfile, env)

    if method == 'GET':
        doShowForm(wfile, env, form)
    elif method == 'POST':
        doPost(wfile, env, form)

SET, ADD_REMOVE = range(1,3)
OPTION_MAP = {
'set_option': SET,
'add_remove_option': ADD_REMOVE,
}

def _buildEntries(form):
    # scan for ddd=On from 'checkbox' fields or id_list='ddd,ddd' from 'hidden' field
    # build the id list ids.
    id_list = form.getfirst('id_list','').split(',')

    wlib = weblib.getMainBm()
    entries = []
    for k in itertools.chain(form.keys(), id_list):
        k = k.strip()
        if not k.isdigit():
            continue
        item = wlib.webpages.getById(int(k))
        if item:
            entries.append(item)
    return entries
    

    
def doPost(wfile, env, form):
    errors = []
    
    entries = _buildEntries(form)
    
    # parse set/add/remove tags
    set_tags = None
    add_tags = None
    remove_tags = None
    option = form.getfirst('option','')
    option = OPTION_MAP.get(option,None)
    if option == SET:
        set_tags = form.getfirst('set_tags','')
    elif option == ADD_REMOVE:
        add_tags = form.getfirst('add_tags','')
        remove_tags = form.getfirst('remove_tags','')
    else:
        errors.append('Please select set tags or add or remove tags.')
    set_tags, unknown1 = weblib.parseTags(wlib, set_tags)
    add_tags, unknown2 = weblib.parseTags(wlib, add_tags)
    remove_tags, unknown3 = weblib.parseTags(wlib, remove_tags)
        
    # deal with new tags
    create_tags = form.getfirst('create_tags','')
    unknown = []
    if (unknown1 or unknown2 or unknown3) and not create_tags:
        unknown = unknown1 + known2 + known3
        tags = u', '.join(unknown)
        errors.append('These tags are not previous used: ' + tags)

    if errors:
        doShowForm(wfile, env, form, errors, new_tags=unknown)
        return
        
    if unknown1:
        set_tags.extend(weblib.create_tags(unknown1))
    if unknown2:
        set_tags.extend(weblib.create_tags(unknown2))

    weblib.organizeEntries(entries, set_tags, add_tags, remove_tags)
    doShowForm(wfile, env, form)####
            
    
def doShowForm(wfile, env, form, errors=None, new_tags=None):
    entries = _buildEntries(form)
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

    EntryOrgRenderer(wfile, env, '').output(errors, new_tags, ids, names, all_tags, some_tags)



# ----------------------------------------------------------------------

class EntryOrgRenderer(response.CGIRendererHeadnFoot):
    TEMPLATE_FILE = 'weblibEntryOrg.html'
    """ 2005-08-19
    con:header
    con:edit_form
            con:id_list
            con:form_title
            con:error
                    con:message
            con:all_tags
            con:some_tags
    con:footer    
    """
    def render(self, node, errors, new_tags, ids, names, all_tags, some_tags):
        node.edit_form.id_list.atts['value'] = ','.join(map(str,ids))
        
        t = string.Template(node.edit_form.form_title.content)
        node.edit_form.form_title.content = t.substitute(total=len(ids), names=names, )
        
        t = string.Template(node.edit_form.all_tags.content)
        node.edit_form.all_tags.content = t.safe_substitute(all_tags=u', '.join(all_tags))
        
        t = string.Template(node.edit_form.some_tags.content)
        node.edit_form.some_tags.content = t.safe_substitute(some_tags=u', '.join(some_tags))

        if errors:
            node.edit_form.error.message.raw = '<br />'.join(bean.errors)
        else:
            node.edit_form.error.omit()

        tags = new_tags and u', '.join(new_tags) or ''
        # TODO: need to escape tags for javascript;
        node.edit_form.new_tags_var.content = node.edit_form.new_tags_var.content % tags


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)
