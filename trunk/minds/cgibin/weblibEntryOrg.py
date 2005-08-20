import cgi
#import datetime
import logging
import os
import sets
import string
import sys

from minds.config import cfg
from minds.cgibin.util import response
from minds import weblib
#from minds.weblib import store
#from minds.weblib import graph

log = logging.getLogger('cgi.weblib')

BASEURL = 'weblib'

## todo: when nothing selected?

def main(rfile, wfile, env):

    form = cgi.FieldStorage(fp=rfile, environ=env)

    wlib = weblib.getMainBm()
    some_tags = sets.Set()##
    title=''##
    for k in form.keys():
        if not k .isdigit():
            continue
        item = wlib.webpages.getById(int(k))
        some_tags.union_update(item.tags)
        title = unicode(item)
    some_tags = map(unicode,some_tags)
    EntryOrgRenderer(wfile, env, '').output(title,some_tags,some_tags)



# ----------------------------------------------------------------------

class EntryOrgRenderer(response.CGIRendererHeadnFoot):
    TEMPLATE_FILE = 'weblibEntryOrg.html'
    """
    con:header
    con:form_title
    con:edit_form
            con:id_list
            con:error
                    con:message
            con:all_tags
            con:some_tags
    con:footer    
    """
    def render(self, node, title, all_tags, some_tags):
        t = string.Template(node.form_title.content)
        node.form_title.content = t.substitute(name=title)
        
        t = string.Template(node.edit_form.all_tags.content)
        node.edit_form.all_tags.content = t.safe_substitute(all_tags=u', '.join(all_tags))
        
        t = string.Template(node.edit_form.some_tags.content)
        node.edit_form.some_tags.content = t.safe_substitute(some_tags=u', '.join(some_tags))


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)
