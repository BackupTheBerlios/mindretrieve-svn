import logging
import os
import sys

from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response

log = logging.getLogger('cgi.update')

def main(rfile, wfile, env):
    req = request.Request(rfile, env)
    url = req.param('url')
    UpdateParentRenderer(wfile).output(url)


# ------------------------------------------------------------------------

class UpdateParentRenderer(response.CGIRenderer):
    TEMPLATE_FILE = 'updateParent.html'
    """
    """
    def render(self, node, url=''):
        node.url.raw = 'var url="%s";' % response.jsEscapeString(url)


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)
