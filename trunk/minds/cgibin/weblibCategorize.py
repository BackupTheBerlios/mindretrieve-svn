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
    CategorizeRenderer(wfile, env, '').output(return_url, [], wlib.category_description)


def doPost(wfile, env, form):
    wlib = store.getMainBm()

    # TODO: parse and analyze
    wlib.category_description = form.getfirst('category_description')

    return_url = request.get_return_url(env, form)
    store.save(wlib)
    response.redirect(wfile, return_url)


# ----------------------------------------------------------------------

class CategorizeRenderer(response.CGIRendererHeadnFoot):
    TEMPLATE_FILE = 'weblibCategorize.html'
    """
    """
    def render(self, node, return_url, errors, category_description):
        node.return_url .atts['value'] = return_url
#        if errors:
#            node.edit_form.error.message.raw = '<br />'.join(errors)
#        else:
#            node.edit_form.error.omit()
        node.category_description.content = category_description


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)
