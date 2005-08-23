"""Application HTTP Server

????

In-process/Fast CGI

  main(rfile, wfile, environ)

To make your script work as regular cgi program, simply add this
statement to the end of your script:

  if __name__ == '__main__':
      main(sys.stdin, sys.stdout, os.environ)

"""

# todo: cache template mod and template, auto update, cache and auto update cgi
# todo: unit test app_httpserver
# todo:   test script exception
# todo:   test should create test cache dir
# todo: support location: status:, buffer output for exception possibility

# todo: need to make sure line breaks in TEST_REQUEST are \r\n
# todo: merge simplehttpserver too, no list dir
# todo: write better description



import SimpleHTTPServer
import logging
import os
import posixpath
import sys
import traceback
import urllib
from StringIO import StringIO

from toollib import HTMLTemplate
from minds.config import cfg
from minds import cgibin
from minds import config
from minds.util import fileutil

log = logging.getLogger('app')



class AppHTTPRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    """Complete HTTP server with GET, HEAD and POST commands.

    GET and HEAD also support running CGI scripts.

    The POST command is *only* implemented for CGI scripts.

    """

    # configurations
    server_version = config.APPLICATION_NAME + "/" + cfg.get('version','number','?')
    protocol_version = "HTTP/1.0"

    # todo: actually these class variables got initialized too early. Before cfg.setup is called from proxy
    docBase = cfg.getPath('docBase')


    # Make rfile unbuffered -- we need to read one line and then pass
    # the rest to a subprocess, so we can't use buffered input.
    rbufsize = 0

    # add .ico
    SimpleHTTPServer.SimpleHTTPRequestHandler.extensions_map.update({
        '.ico': 'image/x-icon',
        })

    def do_POST(self):
        """Serve a POST request.

        This is only implemented for CGI scripts.

        """
        script_name, path_info, query_string = self.parse_cgipath(self.path)
        if self.is_cgi(script_name):
            self.run_cgi(script_name, path_info, query_string)
        else:
            self.send_error(501, "Can only POST to CGI scripts")


    def send_head(self):
        """Version of send_head that support CGI scripts"""
        script_name, path_info, query_string = self.parse_cgipath(self.path)
        if self.is_cgi(script_name):
            return self.run_cgi(script_name, path_info, query_string)
        else:
            return SimpleHTTPServer.SimpleHTTPRequestHandler.send_head(self)


    def is_cgi(self, script_name):
        return cgibin.cgi_registry.get(script_name.lstrip('/'),None)


    def parse_cgipath(self, path):

        # Assume path map to a CGI. Parse the components.
        #
        # general format of a cgi path for app_httpserver
        #   [/SCRIPT_NAME][/PATH_INFO]?[QUERY_STRING]
        #
        # Return SCRIPT_NAME, PATH_INFO, QUERY_STRING

        path, query_string = path.find('?') >= 0 and path.rsplit('?',1) or [path,'']

        i = path.find('/',1)
        if i > 0:
            script_name, path_info = path[:i], path[i:]
        else:
            script_name, path_info = path, ''

        return script_name, path_info, query_string




    def run_cgi(self, script_name, path_info, query_string):
        """Execute a CGI script."""

###        directory, rest = self.cgi_info
###        i = rest.rfind('?')
###        if i >= 0:
###            rest, query = rest[:i], rest[i+1:]
###        else:
###            query = ''
###        i = rest.find('/')
###        if i >= 0:
###            script, rest = rest[:i], rest[i:]
###        else:
###            script, rest = rest, ''

###        if not script:
###            script = 'home' ## todo: magic
###        scriptname = directory + '/' + script

        env = self.makeEnviron(script_name, path_info, query_string)

        #self.send_response(200, "OK")

        parsed_wfile = CGIFileFilter(self.wfile)

        #don't support decoded_query in command line
        # decoded_query = query.replace('+', ' ')

        try:
###            modpath = os.path.join(self.cgiBase, scriptname.lstrip('/'))    # make scriptname relative
###            mod = importModuleByPath(modpath)
            mod = cgibin.cgi_registry.get(script_name.lstrip('/'),None)
            if not mod:
                self.send_error(404, "Not found %s" % self.path)
                return

            # reloading good for development time
            try:
                reload(mod)
            except: # todo: HACK HACK reload does not work in py2exe service version. But it is OK not to reload.
                pass

            mod.main(self.rfile, parsed_wfile, env)
        except Exception:
            log.exception("CGI execution error: %s" % script_name)

            # Original exception already logged. It is OK if below raises new exception


            # todo: is it too late to send these?

            #too late: self.send_response(500)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            out = self.wfile
            out.write('<html><body>')
            out.write('<h1>Internal Error</h1>\n');
            out.write('<pre>\n');
            traceback.print_exc(file=out)
            out.write('</body></html>')


    def makeEnviron(self, script_name, path_info, query_string):
        # Reference: http://hoohoo.ncsa.uiuc.edu/cgi/env.html
        # XXX Much of the following could be prepared ahead of time!
        env = {}
        env['SERVER_SOFTWARE'] = self.version_string()
        env['SERVER_NAME'] = self.server.server_name
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        env['SERVER_PROTOCOL'] = self.protocol_version
        env['SERVER_PORT'] = str(self.server.server_port)
        env['REQUEST_METHOD'] = self.command
        uqrest = urllib.unquote(path_info)
        env['PATH_INFO'] = uqrest
        env['PATH_TRANSLATED'] = self.translate_path(uqrest)
        env['SCRIPT_NAME'] = script_name
        if query_string:
            env['QUERY_STRING'] = query_string
        host = self.address_string()
        if host != self.client_address[0]:
            env['REMOTE_HOST'] = host
        env['REMOTE_ADDR'] = self.client_address[0]
        # XXX AUTH_TYPE
        # XXX REMOTE_USER
        # XXX REMOTE_IDENT
        if self.headers.typeheader is None:
            env['CONTENT_TYPE'] = self.headers.type
        else:
            env['CONTENT_TYPE'] = self.headers.typeheader
        length = self.headers.getheader('content-length')
        if length:
            env['CONTENT_LENGTH'] = length
        accept = []
        for line in self.headers.getallmatchingheaders('accept'):
            if line[:1] in "\t\n\r ":
                accept.append(line.strip())
            else:
                accept = accept + line[7:].split(',')
        env['HTTP_ACCEPT'] = ','.join(accept)
        ua = self.headers.getheader('user-agent')
        if ua:
            env['HTTP_USER_AGENT'] = ua
        rfr = self.headers.getheader('referer')
        if rfr:
            env['HTTP_REFERER'] = rfr
        co = filter(None, self.headers.getheaders('cookie'))
        if co:
            env['HTTP_COOKIE'] = ', '.join(co)
        # XXX Other HTTP_* headers
        #if not self.have_fork:
        #    # Since we're setting the env in the parent, provide empty
        #    # values to override previously set values
        for k in ('QUERY_STRING', 'REMOTE_HOST', 'CONTENT_LENGTH',
                  'HTTP_USER_AGENT', 'HTTP_COOKIE'):
            env.setdefault(k, "")
        return env


    def translate_path(self, path):
        return self.translate_path1(path, self.docBase)


    def translate_path1(self, path, baseDir):
        """Retrofit SimpleHTTPRequestHandler.translate_path() to use
        docBase instead of current directory to look for documents
        """
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = baseDir
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path


    def log_message(self, format, *args):
        log.debug(format, *args)



def importModuleByPath(path):
    """ Convert module name from a path notation into dot notation
        and import with __import__()

        Return module or None
    """
    modFull, modLast = _convertPath2Module(path)
    try:
        mod = __import__(modFull, globals(), locals(), [modLast])
    except Exception:
        log.exception('importModuleByPath: path=%s mod=%s [%s]' % (path, modFull, modLast))
        return None

    # reloading good for development time
    try:
        reload(mod)
    except: # todo: HACK HACK reload does not work in py2exe service version. But it is OK not to reload.
        pass
    return mod



def _convertPath2Module(path):
                                                # e.g. './minds\admin\tmpl/home.html'
    path, ext = os.path.splitext(path)          # strip extension
    path = path.replace('\\','/')               # normalize to /
    path = path.lstrip('.').lstrip('/')         # strip initial . and /
    modLast = os.path.split(path)[1]            # 'home'
    modFull = path.replace('/','.')             # 'minds.admin.tmpl.home'
    return modFull, modLast



def forwardTmpl(wfile, env, tmpl, renderMod, *args):

    # e.g. SCRIPT_NAME='/admin/snoop.py', tmpl='tmpl/home.html'

    #scriptname = env.get('SCRIPT_NAME','')                          # '/admin/snoop.py'
    #scriptpath, scriptfile = os.path.split(scriptname.lstrip('/'))  # 'admin', 'snoop'

    tmplPathname = os.path.join(cfg.getPath('docBase'), tmpl)

    # invoke tmpl's render() method
    fp = file(tmplPathname)

    template = HTMLTemplate.Template(renderMod.render, fp.read())
    wfile.write(template.render(*args))


## TODO: clean up
## cleaned up version of forwardTmpl()
#def forwardTmpl1(wfile, tmpl, render, *args):
#
#    tmplPathname = os.path.join(cfg.getPath('docBase'), tmpl)
#    fp = file(tmplPathname,'rb')
#
#    template = HTMLTemplate.Template(render, fp.read())
#
#    wfile.write(template.render(*args))



class CGIFileFilter(fileutil.FileFilter):
    """ Used to wrap the output file for the CGI program.
        Looking for server directive and send corresponding HTTP status
        for the CGI program.
        Only check for server directive in the first line.
        The rest of output is pass thru.
    """

    def __init__(self,fp):
        super(CGIFileFilter, self).__init__(fp)
        self.buf = []
        self.parsed = False


    def write(self,str):
        if self.parsed:
            self.fp.write(str)
        else:
            self.buf.append(str)
            if '\n' in str:
                self._parseLines()


    def writelines(self,sequence):
        raise NotImplementedError()
        #if self.parsed:
        #    self.fp.writelines(sequence)
        #else:
        #    for line in sequence:
        #        self.write(line)


    def _parseLines(self):
        lines = ''.join(self.buf).split('\n',1)
        self._parseLine(lines[0])
        self.parsed = True
        self.fp.write('\n'.join(lines[1:]))


    def _parseLine(self, line):

        if len(line) >= 3:
            if line[:3].isdigit():
                self.fp.write('HTTP/1.0 ')
                self.fp.write(line)
                self.fp.write('\n')
                return

        nv = line.split(':')
        if nv[0].strip().lower() == 'location':
            self.fp.write('HTTP/1.0 302 Found\r\n')
            self.fp.write(line)
            self.fp.write('\n')
            return

        self.fp.write('HTTP/1.0 200 OK\r\n')
        self.fp.write(line)
        self.fp.write('\n')





### Testing ############################################################

__test_doc__ = """Usage: app_httpserver.py path

Test a CGI script locally
"""

SAMPLE_GET_REQUEST = """GET %s HTTP/1.0\r
User-Agent: test_agent\r
Host: localhost\r
\r
"""

SAMPLE_POST_REQUEST = """POST %s HTTP/1.0\r
User-Agent: test_agent\r
Host: localhost\r
Content-Type: text\r
Content-Length: 14\r
\r
data1
data2
"""

SAMPLE_GET_REQUEST1 = """GET %s HTTP/1.0\r
User-Agent: test_agent\r
Host: localhost\r
Content-Type: text\r
Content-Length: 14\r
\r
data1
data2
"""

class DummyServer:
    server_name = 'Dummy Server'
    server_port = 0


def handlePath(path, wfile):
    """ Test handler. Invoke AppHTTPRequestHandler without starting a web server. """

    from minds.util.fileutil import FileSocket

    request = SAMPLE_GET_REQUEST % path
    rfile = StringIO(request)
    client_soc = FileSocket(rfile, wfile)
    client_address = ('127.0.0.1', 0)
    server = DummyServer()
    AppHTTPRequestHandler(client_soc, client_address, server)


def main():
    ''' Invoke AppHTTPRequestHandler from command line '''

    if len(sys.argv) <= 1:
        print __test_doc__
        sys.exit(-1)

    path = sys.argv[1]
    handlePath(path, sys.stdout)

# todo: sys.stdout has mode 'w' should be 'wb'

#def test_forwardTmpl():
#    env = { 'SCRIPT_NAME' : '/admin/snoop.py' }
#    forwardTmpl(sys.stdout, env, 'tmpl/home.html', 'now')


if __name__ == '__main__':
    # must import itself; otheriwse top level script is imported as __main__
    from minds import app_httpserver
    app_httpserver.main()
