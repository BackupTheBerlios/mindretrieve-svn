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
        '%s/weblib/_?url='+encodeURIComponent(d.location)+'&title='+encodeURIComponent(d.title)+'&description='+encodeURIComponent(ds),
        'weblibForm', s);
    win.focus();
    void(0);
"""

def buildBookmarklet():
    b = BOOKMARKLET % getMindRetrieveBaseURL()
    # dehydrate spaces
    b = b.replace('\n','').replace(' ','')
    return b


def getMindRetrieveBaseURL():
    port = cfg.getint('http.admin_port')
    return 'http://localhost:%s' % port


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


    def render(self, node, *args):
        # To be overridden by user
        raise NotImplementedError()



# ----------------------------------------------------------------------

def _split_style_script_block(text):
    """
    Parse text and extract the style and script block.
    We do simple search for <style> and </style> only. Make sure you
    don't use anything fancy in your template.
    Also <script> comes before <script>.

    @return
        style text (without the style tag) or '',
        script text (without the script tag) or '',
        rest of text
    """
    # extract <style>
    style_text = ''
    b = text.find('<style>')
    e = text.rfind('</style>')
    if b >= 0 and e >= 0:
        e += len('</style>')
        style_text = text[b:e]
        text = text[:b] + text[e:]

    # extract <script>
    script_text = ''
    b = text.find('<script>')
    e = text.rfind('</script>')
    if b >= 0 and e >= 0:
        e += len('</script>')
        script_text = text[b:e]
        text = text[:b] + text[e:]

    return style_text, script_text, text


class WeblibLayoutRenderer(CGIRenderer):
    """
    Put the output of CGIRender within the WeblibLayout.html
    """

    LAYOUT_TMPL = 'weblibLayout.html'

    def __init__(self, *args, **kargs):
        CGIRenderer.__init__(self, *args, **kargs)
        self.title          = ''
        self.querytxt       = ''

        self.style_block    = ''
        self.script_block   = ''
        self.content_text   = ''


    def setLayoutParam(self, title='', querytxt=''):
        self.title          = title
        self.querytxt       = querytxt


    def render_layout(self, node):
        if self.title:
            node.title.content = self.title
        node.querytxt.atts['value'] = self.querytxt
        node.bookmarklet.atts['href'] = buildBookmarklet()

        # a simplistic way to insert style in the <head> block and the body in the <body> block.
        node.contentStyle.raw = self.style_block
        node.contentScript.raw = self.script_block
        node.contentBody.raw = self.content_text


    def output(self, *args):
        # generates the content first
        self.content_text = self.template.render(*args)
        self.style_block, self.script_block, self.content_text = _split_style_script_block(self.content_text)

        # render the layout frame; insert content inside
        tpath = cfg.getpath('docBase')/self.LAYOUT_TMPL
        fp = tpath.open('rb')
        try:
            tmpl = fp.read()
        finally:
            fp.close()
        layoutTemplate = HTMLTemplate.Template(self.render_layout, tmpl)
        output = layoutTemplate.render()

        self.out.write(output)


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