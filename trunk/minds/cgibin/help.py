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
    path = env.get('PATH_INFO', '')
    if path == '/GettingStarted':
        doGettingStarted(wfile)
    elif path == '/ProxyInstruction':
        renderer = ProxyInstructionRenderer(wfile)
        renderer.setLayoutParam('MindRetrieve - Proxy Instruction')
        renderer.output()
    else:
        # filler
        doGettingStarted(wfile)


def doGettingStarted(wfile):
    renderer = GettingStartedRenderer(wfile)
    renderer.setLayoutParam('MindRetrieve - Getting Started')
    renderer.output()


#------------------------------------------------------------------------

class GettingStartedRenderer(response.WeblibLayoutRenderer):
    TEMPLATE_FILE = 'gettingStarted.html'
    def render(self, node):
        node.mindretrieveURL.atts['href'] = '%s/' % response.getMindRetrieveBaseURL()
        node.importURL.atts['href'] = '%s/weblib/import' % response.getMindRetrieveBaseURL()
        node.bookmarkletURL.atts['href'] = response.buildBookmarklet()
        node.proxyPort.content = str(cfg.getint('http.proxy_port'))

class ProxyInstructionRenderer(response.WeblibLayoutRenderer):
    TEMPLATE_FILE = 'proxyInstruction.html'
    def render(self, node):
        pass



if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)
