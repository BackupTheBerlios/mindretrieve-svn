"""Usage:
"""

import cgi
import ConfigParser
import codecs
import datetime
import logging
import sys
import threading
import mimetypes, posixpath
import zipfile

from minds.config import cfg
from minds import distillparse
from minds import docarchive
import docreaderTmpl


CONFIG_INI = 'docreader.ini'

lock = threading.RLock()
g_openedfile = None
g_config_item = None


class OpenedFile(object):
    """ Object to encapsulate a opened zip file.
        Also maintain a logic to close it after some timeout.
    """

    TIMEOUT = 60.0

    def __init__(self, path):
        self.path = path
        self.fp = file(path,'rb')
        self.zf = zipfile.ZipFile(self.fp, 'r')
        self.timer = None
        self.lastUse = datetime.datetime.now()


    def setCloseTimer():
        if not self.timer:
            self.timer = threading.Timer(self.TIMEOUT, self.close)
            self.timer.start()


    def close(self):
        lock.acquire()
        try:
            timeout2 = self.TIMEOUT - 3   # reduce by an arbitrary 3 to account for timer limitation
            if datetime.datetime.now() - self.lastUse < datetime.timedelta(seconds=timeout2):
                # do not close now, set another timer instead
                self.timer = None
                self.setCloseTimer()
                return

            if self.zf: self.zf.close()
            if self.fp: self.fp.close()
            self.path = ''
            self.zf = None
            self.fp = None

            global g_openedfile
            g_openedfile = None

        finally:
            lock.release()


    def acquire(path):
        global g_openedfile
        if g_openedfile and g_openedfile.path == path:
            g_openedfile.lastUse = datetime.datetime.now()  # we have no good way to stop the timer.
                                                            # Updating lastUse so that close() would give it more time.
            return g_openedfile

        g_openedfile = OpenedFile(path)
        return g_openedfile

    acquire = staticmethod(acquire)



class Documentation(object):

    def __init__(self, name):
        self.name = name
        self.path = ''
        self.bookmark = {'':''}

    def __str__(self):
        return 'name=%s path=%s bookmark=%s' % (self.name,self.path,self.bookmark)



def getConfig(forceload=False):
    """ Read and parse config ini """
    global g_config_item
    if g_config_item and not forceload:
        return g_config_item

    cp = ConfigParser.ConfigParser()
    cp.read(CONFIG_INI)

    itemDir = {}
    for name, path in cp.items('documentation'):
        doc = Documentation(name)
        doc.path = path
        itemDir[name] = doc

    for name, path in cp.items('bookmark'):
        if '#' in name:
            name, frag = name.split('#',1)
        else:
            frag = ''

        if not itemDir.has_key(name):
            continue

        doc = itemDir[name]
        doc.bookmark[frag] = path

    g_config_item = itemDir
    return g_config_item



def doDirectory(rfile, wfile, env):
    config_item = getConfig(True)

    wfile.write(
"""Content-type: text/html\r
\r
""")
    from minds import app_httpserver
    app_httpserver.forwardTmpl(wfile, env, 'docreader.html',
        docreaderTmpl, '', config_item)



def doGetResource(rfile, wfile, env, path_info):


    path_info = path_info.lstrip('/')
    if path_info.find('/') >= 0:
        name, path = path_info.split('/',1)
    else:
        name, path = path_info, ''              # need redirect

    docsDict = getConfig()
    documentation = docsDict[name]  # todo: 404



    lock.acquire()
    try:
        openedfile = OpenedFile.acquire(documentation.path)
        ctype = guess_type(path)
        if ctype.startswith('text/'):
            ctype += '; charset=UTF-8'
            sw = codecs.getwriter('utf-8')
            wfile = sw(wfile,'replace')

        ### todo: 404  todo: charset

        wfile.write(
"""Content-type: %s\r
\r
""" % ctype)

        wfile.write( openedfile.zf.read(path))

    finally:
        lock.release()



def guess_type(path):
    base, ext = posixpath.splitext(path)
    extensions_map = mimetypes.types_map.copy()
    if ext in extensions_map:
        return extensions_map[ext]
    ext = ext.lower()
    if ext in extensions_map:
        return extensions_map[ext]
    else:
        return 'application/octet-stream' # Default



def main(rfile, wfile, env):

    form = cgi.FieldStorage(fp=rfile, environ=env)

    path_info = env['PATH_INFO']
    if path_info:
        doGetResource(rfile, wfile, env, path_info)
    else:
        doDirectory(rfile, wfile, env)



if __name__ == "__main__":

    #main(sys.stdin, sys.stdout, os.environ)
    import pprint
    pprint.pprint( getConfig(True) )
