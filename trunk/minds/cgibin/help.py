import cgi  ###TODO?
import logging
import os
import sys

from minds import qmsg_processor
from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds.util import httputil
from minds.util import pagemeter

log = logging.getLogger('cgi.help')


def main(rfile, wfile, env):
    req = request.Request(rfile, env)
    path = env.get('PATH_INFO', '')
    if path == '/GettingStarted':
        doGettingStarted(wfile, req)
    elif path == '/ProxyInstruction':
        renderer = ProxyInstructionRenderer(wfile)
        renderer.setLayoutParam('MindRetrieve - Getting Started', '', response.buildBookmarklet(req.env))
        renderer.output()
    else:
        # filler
        doGettingStarted(wfile, req)


def doGettingStarted(wfile,req):
    renderer = GettingStartedRenderer(wfile)
    renderer.setLayoutParam('MindRetrieve - Getting Started', '', response.buildBookmarklet(req.env))
    renderer.output(response.buildBookmarklet(req.env))


#------------------------------------------------------------------------

class GettingStartedRenderer(response.WeblibLayoutRenderer):
    TEMPLATE_FILE = 'gettingStarted.html'
    def render(self, node, bookmarkletURL):
        node.bookmarklet.atts['href'] = bookmarkletURL


class ProxyInstructionRenderer(response.WeblibLayoutRenderer):
    TEMPLATE_FILE = 'proxyInstruction.html'
    def render(self, node,):
        pass



if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)
