"""Usage: response.py template_filename
"""

import codecs
import os.path
import sys

from minds.config import cfg
from toollib import HTMLTemplate


# ----------------------------------------------------------------------
# construct header common between pages

HEADER_TMPL = 'header.html'
REMOVE = '<!-- remove above -->'

def getHeader(querytxt=''):
    pathname = os.path.join(cfg.getPath('docBase'), HEADER_TMPL)
    fp = file(pathname,'rb')
    try:
        template = HTMLTemplate.Template(renderHeader, fp.read())
    finally:
        fp.close()

    header_text = template.render(querytxt)
    
    # remove some excess from header_text to make it embeddable.
    # raise exception if REMOVE is not found
    i = header_text.index(REMOVE)
    header_text = header_text[i+len(REMOVE):]
    return header_text
    
    
def renderHeader(node, querytxt):
    node.querytxt.atts['value'] = querytxt


# ----------------------------------------------------------------------

class ResponseTemplate(object):
    """ Base class of responses """

    def __init__(self, wfile, template_name,
        content_type='text/html',
        encoding='utf-8',
        cache_control='no-cache'):

        # load template
        pathname = os.path.join(cfg.getPath('docBase'), template_name)
        fp = file(pathname,'rb')
        try:
            self.template = HTMLTemplate.Template(self.render, fp.read())
        finally:    
            fp.close()
        
        # HTTP header    
        wfile.write('Content-type: %s; charset=%s\r\n' % (content_type, encoding))
        if cache_control:
            wfile.write('Cache-control: %s\r\n' % (cache_control,))
        wfile.write('\r\n')

        # build encoded output stream
        self.out = codecs.getwriter(encoding)(wfile,'replace')


    def output(self, *args):
        self.out.write(self.template.render(*args))
        
        
    def render(self, node):
        pass    






def main(argv):
    """ Helper to show structure of template """
    fp = file(argv[1],'rb')
    template = HTMLTemplate.Template(None, fp.read())
    print template.structure()


if __name__ == '__main__':
    main(sys.argv)