"""Usage: response.py template_filename
"""

import codecs
import os.path
import sys

from minds.config import cfg
from toollib import HTMLTemplate


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