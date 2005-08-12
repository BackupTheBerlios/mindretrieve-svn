"""Usage: response.py template_filename
"""

import codecs
import os.path
import sys

from minds.config import cfg
from toollib import HTMLTemplate


# ----------------------------------------------------------------------

BOOKMARKLET = """
javascript:
    d=document;
    u=d.location;
    t=d.title;
    ds='';
    mt=d.getElementsByTagName('meta');
    for(i=0;i<mt.length;i++){
        ma=mt[i].attributes;
        na=ma['name'];
        if(na&&na.value.toLowerCase()=='description'){
            ds=ma['content'].value;
        }
    }
    d.location='http://%s/weblib/_?u='+encodeURIComponent(u)+'&t='+encodeURIComponent(t)+'&ds='+encodeURIComponent(ds);
"""

def buildBookmarklet(env):
    # find host & port from CGI environment
    host = env.get('SERVER_NAME','')
    port = env.get('SERVER_PORT','80')
    # SERVER_NAME is actually not that good. Override with 'localhost'
    host = 'localhost'
    
    b = BOOKMARKLET % ('%s:%s' %  (host, port))
    # space dehydration
    return b.replace('\n','').replace(' ','')  


# ----------------------------------------------------------------------
# construct common header and footer

HEADER_TMPL = 'header.html'
FOOTER_TMPL = 'footer.html'
REMOVE = '<!-- remove above -->'

def _format_template(tmpl, render, *args):
    """ helper to render header and footer """
    
    pathname = os.path.join(cfg.getPath('docBase'), tmpl)
    fp = file(pathname,'rb')
    try:
        template = HTMLTemplate.Template(render, fp.read())
    finally:
        fp.close()

    text = template.render(*args)
    
    # remove some extra data from text to make it embeddable.
    # raise exception if REMOVE is not found
    i = text.index(REMOVE)
    return text[i+len(REMOVE):]


def getHeader(querytxt=''):
    return _format_template(HEADER_TMPL, renderHeader, querytxt)
    
    
def renderHeader(node, querytxt):
    node.querytxt.atts['value'] = querytxt


def getFooter(env):
    b = buildBookmarklet(env)
    return _format_template(FOOTER_TMPL, renderFooter, b)

    
def renderFooter(node, href):
    node.bookmarklet.atts['href'] = href.replace("'",'&apos;')


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