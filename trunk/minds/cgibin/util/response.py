"""Usage: response.py template_filename

Run from command line to display the HTMLTemplate parse tree.
"""
import codecs
import datetime
import sys
import urllib

from minds.config import cfg
from toollib import HTMLTemplate


ASCII = ''.join(map(chr,range(0x20, 0x80)))

def redirect(wfile, url):
    # 2005-08-24 TODO
    # wikipedia uses http encoded utf-8 encoded unicode string in links.
    #   e.g. http://zh.wikipedia.org/wiki/%E5%85%8B%E9%87%8C%E5%A7%86%E6%9E%97%E5%AE%AB
    # Opera seems over zealous for converting it into unicode (in document.location).
    # This seems to be the main reason we end up with unicode URL here.
    # Can we count on servers in general to accept UTF-8 encoded characters???

    # only use this to quote non-ASCII characters
    url = urllib.quote(url.encode('utf8'), ASCII)
    wfile.write('location: %s\r\n\r\n' % url)


def jsEscapeString(s):
    """ Escape s for use as a Javascript String """

    # 2005-12-12 note:
    # < and > are not suppose to require escaping.
    # But HTML parsers seems to aggressively terminate a string when
    # they see "</script>". Try this in your browser.

    """
    <script>
      alert('Escaped \x3c/script\x33\x3cfont size=7 color=red\x3eGOTCHA');
      alert('Unescaped </script><font size=7 color=red>GOTCHA');
    </script>
    This is the HTML body
    """

    # Note: non-ascii unicode characters do not need encoding

    return s.replace('\\','\\\\') \
        .replace('\r', '\\r') \
        .replace('\n', '\\n') \
        .replace('"', '\\"') \
        .replace("'", "\\'") \
        .replace("<", '\\x3C') \
        .replace(">", '\\x3E')

# ----------------------------------------------------------------------

BOOKMARKLET = """
javascript:
    d=document;
    mt=d.getElementsByTagName('meta');
    ds='';
    for(i=0;i<mt.length;i++){
        ma=mt[i].attributes;
        na=ma['name'];
        if(na&&na.value.toLowerCase()=='description'){
            ds=ma['content'].value;
        }
    }
    h = window.innerHeight * 0.6;
    w = window.innerWidth * 0.8;
    s = 'width=' + w + ',height=' + h;
    win = window.open(
        'http://%s/weblib/_?url='+encodeURIComponent(d.location)+'&title='+encodeURIComponent(d.title)+'&description='+encodeURIComponent(ds),
        'weblibForm', s);
    win.focus();
    void(0);
"""

def buildBookmarklet(env):
    # find host & port from CGI environment
    host = env.get('SERVER_NAME','')
    port = env.get('SERVER_PORT','80')
    # SERVER_NAME is actually not that good. Override with 'localhost'
    host = 'localhost'

    b = BOOKMARKLET % ('%s:%s' %  (host, port))
    # dehydrate spaces
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
        tpath = cfg.getpath('docBase')/self.TEMPLATE_FILE
        fp = tpath.open('rb')
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
        tpath = cfg.getpath('docBase')/tmpl
        fp = tpath.open('rb')
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
    filename = argv[1]
    pathname = cfg.getpath('docBase')/filename
    print
    print 'File:', pathname
    print 'Date:',str(datetime.datetime.now())[:19]
    fp = file(pathname,'rb')
    template = HTMLTemplate.Template(None, fp.read())
    print template.structure()


if __name__ == '__main__':
    main(sys.argv)