"""Usage: response.py template_filename

Run from command line to display the HTMLTemplate parse tree.
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

class CGIRenderer(object):
    """ 
    Base class of CGI responses.
    1. Open and compile HTMLTemplate.
    2. Output HTTP headers including Content-type and encoding.
    3. Prepare an encoding output stream.
    4. Execute the template render() method and sent output to wfile.
    
    User should:
    1. Subclass CGIRenderer and implement the render method.
    2. Instantiate a CGIRenderer subclass, provide wfile, etc, as arguments.
    3. Invoke the output method, provide the template specific arguments.    
    """
    
    # template filename to be overriden by user.
    TEMPLATE_FILE = None     

    def __init__(self, wfile, 
        content_type='text/html',
        encoding='utf-8',
        cache_control='no-cache'):

        # load template
        pathname = os.path.join(cfg.getPath('docBase'), self.TEMPLATE_FILE)
        fp = file(pathname,'rb')
        try:
            self.template = HTMLTemplate.Template(self._render0, fp.read())
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
        
        
    def _render0(self, node, *args):
        # To be overridden by subclass to define pre-render logic
        self.render(node, *args)
        
        
    def render(self, node, *args):
        # To be overridden by user
        raise NotImplementedError()    



# ----------------------------------------------------------------------

class CGIRendererHeadnFoot(CGIRenderer):
    """
    A CGIRenderer with header and footer substitution.
    """
    HEADER_TMPL = 'header.html'
    FOOTER_TMPL = 'footer.html'
    REMOVE_TEXT = '<!-- remove above -->'

    def __init__(self, wfile, env, querytxt='', *args):
        super(CGIRendererHeadnFoot, self).__init__(wfile, *args)
        self.env = env
        self.querytxt = querytxt
        
    def _format_template(self, tmpl, render, *args):
        """ helper to render header and footer """
        pathname = os.path.join(cfg.getPath('docBase'), tmpl)
        fp = file(pathname,'rb')
        try:
            template = HTMLTemplate.Template(render, fp.read())
        finally:
            fp.close()
        text = template.render(*args)
        
        # remove some extra data from text to make it embeddable.
        # raise exception if REMOVE_TEXT is not found
        i = text.index(self.REMOVE_TEXT)
        return text[i+len(self.REMOVE_TEXT):]

    def _renderHeader(self, node, querytxt):
        node.querytxt.atts['value'] = querytxt
        
    def _renderFooter(self, node, href):
        node.bookmarklet.atts['href'] = href.replace("'",'&apos;')

    def _render0(self, node, *args):
        b = buildBookmarklet(self.env)
        node.header.raw = self._format_template(self.HEADER_TMPL, self._renderHeader, self.querytxt)
        node.footer.raw = self._format_template(self.FOOTER_TMPL, self._renderFooter, b)
        self.render(node, *args)



# ----------------------------------------------------------------------

def main(argv):
    """ Helper to show structure of template """
    fp = file(argv[1],'rb')
    template = HTMLTemplate.Template(None, fp.read())
    print template.structure()


if __name__ == '__main__':
    main(sys.argv)