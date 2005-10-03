import cgi
#import itertools
import logging
#import os
#import sets
#import string
import sys

from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import store

log = logging.getLogger('cgi.categry')

def main(rfile, wfile, env):
    method, form, _, _ = request.parseURL(rfile, env)
    if method == 'POST':
        doPost(wfile, env, form)
    else:
        doShowForm(wfile, env, form)


def doShowForm(wfile, env, form):
    wlib = store.getMainBm()
    return_url = request.get_return_url(env, form)
    uncategorized = [(unicode(tag).lower(), unicode(tag)) for tag in wlib.uncategorized]
    uncategorized.sort()
    uncategorized = [t for l,t in uncategorized]
    CategorizeRenderer(wfile, env, '').output(return_url, [], wlib.category_description, uncategorized)


def doPost(wfile, env, form):
    wlib = store.getMainBm()

    # TODO: parse and analyze
    wlib.category_description = form.getfirst('category_description').decode('utf-8')

    from minds.util import dsv
    data = dsv.encode_fields(['@0', '', wlib.category_description] + [''] * (10-3))
    print >>sys.stderr, data

    wlib.categorize()

    return_url = request.get_return_url(env, form)
    store.save(wlib)
    response.redirect(wfile, return_url)


# ----------------------------------------------------------------------

class CategorizeRenderer(response.CGIRendererHeadnFoot):
    TEMPLATE_FILE = 'weblibCategorize.html'
    """ 2005-10-03
    tem:
        con:header
        con:return_url
        con:category_description
        rep:uncategorized_tag
        con:footer
    """
    def render(self, node, return_url, errors, category_description, uncategorized):
        node.return_url .atts['value'] = return_url
#        if errors:
#            node.edit_form.error.message.raw = '<br />'.join(errors)
#        else:
#            node.edit_form.error.omit()
        node.category_description.content = category_description
        node.uncategorized_tag.repeat(self.render_uncategorized_tag, uncategorized)


    def render_uncategorized_tag(self, node, item):
        node.content = unicode(item)


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)
