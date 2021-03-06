"""Application HTTP Server

In-process/Fast CGI HTTP server base on SimpleHTTPServer.SimpleHTTPRequestHandler.

A CGI should define this method:

  main(rfile, wfile, environ)

To make your script work as regular cgi program, simply add this
statement to the end of your script:

  if __name__ == '__main__':
      main(sys.stdin, sys.stdout, os.environ)
"""


import logging
import os
import posixpath
import SimpleHTTPServer
import sys
import traceback
import urllib
from StringIO import StringIO

from minds.config import cfg
from minds import base_config
from minds.util import fileutil
from toollib import HTMLTemplate

log = logging.getLogger('app')



class AppHTTPRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    """
    Complete HTTP server with GET, HEAD and POST commands.
    GET and HEAD also support running CGI scripts.
    The POST command is *only* implemented for CGI scripts.
    """

    # configurations
    server_version = cfg.application_name
    protocol_version = "HTTP/1.0"

    # todo: actually these class variables got initialized too early. Before cfg.setup is called from proxy
    docBase = cfg.getpath('docBase')

    # Make rfile unbuffered -- we need to read one line and then pass
    # the rest to a subprocess, so we can't use buffered input.
    rbufsize = 0

    # add .ico
    SimpleHTTPServer.SimpleHTTPRequestHandler.extensions_map.update({
        '.ico': 'image/x-icon',
        })

    def version_string(self):
        return self.server_version


    def do_POST(self):
        """
        Serve a POST request.
        This is only implemented for CGI scripts.
        """
        cgi_info = self._lookup_cgi(self.path)
        if cgi_info:
            self.run_cgi(cgi_info)
        else:
            self.send_error(501, "Can only POST to CGI scripts")


    def send_head(self):
        """Common code for GET and HEAD commands.

        This version reimplement much of
        SimpleHTTPServer.SimpleHTTPRequestHandler as it is
        unfortunately not very parameterized.

        In addition this added support of CGI scripts.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        cgi_info = self._lookup_cgi(self.path)
        if cgi_info:
            return self.run_cgi(cgi_info)

        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            # have to be file, no directory listing support
            self.send_error(404, "File not found")
            return None

        f = None
        ctype = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", ctype)
        self.send_header("Content-Length", str(os.fstat(f.fileno())[6]))
        self.send_header("Cache-Control", "max-age=86400")  # static files assume good for 1 day
        self.end_headers()
        return f


    def _lookup_cgi(self, path):
        """
        Parse the path and Lookup CGI registry.

        general format of a cgi path for app_httpserver
          [/SCRIPT_NAME][/PATH_INFO]?[QUERY_STRING]

        @return module, /SCRIPT_NAME, /PATH_INFO, QUERY_STRING or None
        """
        if not path: path = '/' # just in case

        from minds import cgibin
        for name, mod in cgibin.cgi_registry:
            if not path.startswith(name):
                continue
            path_info = path[len(name):]
            if path_info and path_info[0] not in ['/','?']:
                continue # not a match
            if '?' in path_info:
                path_info, query_string = path_info.split('?',1)
            else:
                query_string = ''
            return mod, name, path_info, query_string
        return None


    def run_cgi(self, cgi_info):
        """ Execute a CGI script. cgi_info is the value returned from _lookup_cgi() """

        mod, script_name, path_info, query_string = cgi_info
        env = self.makeEnviron(script_name, path_info, query_string)

        parsed_wfile = CGIFileFilter(self.wfile)

        #don't support decoded_query in command line
        # decoded_query = query.replace('+', ' ')

        # reloading good for development time
        try:
            reload(mod)
        except: # todo: HACK HACK reload does not work in py2exe service version. But it is OK not to reload.
            pass

        try:
            mod.main(self.rfile, parsed_wfile, env)
            parsed_wfile.flush()
        except:
            log.exception("CGI execution error: %s" % script_name)
            if parsed_wfile.state >= parsed_wfile.SENT:
                log.error("CGI content already sent")
                # meaning the error page below would be precede by some faulty output

            # Original exception already logged. It is OK if below raises new exception
            self.send_response(500)
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

    # invoke tmpl's render() method
    fp = file(cfg.getpath('docBase') / tmpl)

    template = HTMLTemplate.Template(renderMod.render, fp.read())
    wfile.write(template.render(*args))

# TODO: clean up
# cleaned up version of forwardTmpl()


#------------------------------------------------------------------------

class CGIFileFilter(fileutil.FileFilter):
    """
    Used to wrap the output file for the CGI program.
    Looking for server directive and send corresponding HTTP status
    for the CGI program.
    Only check for server directive in the first line.
    The rest of output is pass thru.
    """

    # define CGI output states
    (
    INIT,           # waiting for the first line of output
    BUFFER,         # first line parsed, continue buffering
    SENT,           # buffered has filled, some output has sent to recipient
    ) = range(3)
    MAX_BUFFER = 1000000

    def __init__(self,fp):
        super(CGIFileFilter, self).__init__(fp)
        self.init_buf = StringIO()  # buffer to use in INIT state
        self.buf = StringIO()       # buffer to use in BUFFER state
        self.state = self.INIT


    def write(self,str):
        if self.state >= self.SENT:
            self.fp.write(str)

        elif self.state >= self.BUFFER:
            self.buf.write(str)
            if self.buf.len > self.MAX_BUFFER:
                self.flush()

        elif '\n' in str:
            before, after = str.split('\n',1)
            self._parseLine(self.init_buf.getvalue()+before)
            self.state = self.BUFFER
            self.buf.write(after)
            if self.buf.len > self.MAX_BUFFER:
                self.flush()

        else:
            self.init_buf.write(str)


    def writelines(self,sequence):
        raise NotImplementedError()
        #if self.parsed:
        #    self.fp.writelines(sequence)
        #else:
        #    for line in sequence:
        #        self.write(line)


    def flush(self):
        if self.buf:
            self.fp.write(self.buf.getvalue())
            self.buf = None
        self.state = self.SENT


    def _parseLine(self, line):
        # Reference CGI Script Output http://hoohoo.ncsa.uiuc.edu/cgi/out.html

        assert not self.buf.getvalue()
        if len(line) >= 3:
            # is format: nnn xxxxx?
            if line[:3].isdigit():
                self.buf.write('HTTP/1.0 ')
                self.buf.write(line)
                self.buf.write('\n')
                return

        nv = line.split(':')
        # is format: Location url?
        if nv[0].strip().lower() == 'location':
            self.buf.write('HTTP/1.0 302 Found\r\n')
            self.buf.write(line)
            self.buf.write('\n')
            return

        # no match of parsed header
        self.buf.write('HTTP/1.0 200 OK\r\n')
        self.buf.write(line)
        self.buf.write('\n')




#------------------------------------------------------------------------
# Command line invoker

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
    """ Invoke AppHTTPRequestHandler from command line """
    if len(sys.argv) <= 1:
        print __test_doc__
        sys.exit(-1)
    path = sys.argv[1]
    handlePath(path, sys.stdout)
    # note: sys.stdout has mode 'w'. Ideally it should be 'wb'.


if __name__ == '__main__':
    # must import itself; otheriwse top level script is imported as __main__
    from minds import app_httpserver
    app_httpserver.main()
