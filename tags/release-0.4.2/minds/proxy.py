""" MindSearch Main Program
"""

import logging
import os, os.path, sys
import threading

# it is recommend that all modules load cfg from config at the beginning.
# it loads the test setup and help prepare basic logging
from config import cfg

import app_httpserver
import config
import httpserver
import proxyhandler
import qmsg_processor
#import urifs
from minds.util import threadutil



### System Globals #####################################################

CONFIG_FILENAME = 'config.ini'
log = logging.getLogger('proxy')
_shutdownEvent = threading.Event()



########################################################################

class runnable(object):
    def __init__(self, callable, *args):
        self.callable = callable
        self.args = args
    def run(self):
        self.callable(*self.args)


proxy_httpd = None

def proxyMain():
    port = cfg.getint('http','proxy_port')
    numThreads = cfg.getint('http','proxy_threads', 1)
    server_address = ('', port)
    global proxy_httpd
    proxy_httpd = httpserver.PooledHTTPServer(server_address, proxyhandler.ProxyHandler, numThreads)
    log.info('Proxy: %s', proxy_httpd.report_config())
    proxy_httpd.serve_forever()


admin_httpd = None

def adminMain():
    port = cfg.getint('http','admin_port')
    server_address = ('', port)
    global admin_httpd
    admin_httpd = httpserver.HTTPServer(server_address, app_httpserver.AppHTTPRequestHandler)
    log.info("Start admin on '%s' port %s" % server_address)
    app_httpserver.log.info('app_httpserver setup: docBase=%s',
        app_httpserver.AppHTTPRequestHandler.docBase)

    admin_httpd.serve_forever()


def indexMain():
    interval = cfg.getint('indexing','interval',3)
    log.info('Scheduled index thread to run every %s minutes' % interval)
    while not _shutdownEvent.wait(interval * 60):
        if _shutdownEvent.isSet():
            break
        qmsg_processor.backgroundIndexTask()



########################################################################

def init(config_filename):
    """ Basic configuration. Designed to be light weight enough to invoke for unit testing. """

    cfg.load(config_filename)
    cfg.setupPaths()


def setup():
    """ module startup """
    setupLogging()
    #urifs.init()


def setupLogging():
    filename = os.path.join(cfg.getPath('logs'), 'system.log')
    hdlr = logging.handlers.RotatingFileHandler(filename, 'a', 1100000, 4)
    formatter = logging.Formatter('%(asctime)s %(name)-10s - %(message)s')
    hdlr.setFormatter(formatter)
    rootlog = logging.getLogger()
    rootlog.addHandler(hdlr)
    rootlog.removeHandler(config.bootstrapHdlr)
    rootlog.setLevel(logging.DEBUG)

    # redirect stdout and stderr to log
    stdoutFp = LogFileObj(logging.getLogger('stdout'))
    stderrFp = LogFileObj(logging.getLogger('stderr'))
    sys.stdout = stdoutFp
    sys.stderr = stderrFp
    print 'stdout ready'
    print >>sys.stderr, 'stderr ready'


class LogFileObj(object):
    def __init__(self,log):
        self.log = log
        self.lst = []

    def write(self,str):
        self.lst.append(str)
        if '\n' in str:
            self.flush()

    def writelines(self,sequence):
        self.flush()
        for line in sequence:
            self.log.debug(line)

    def flush(self):
        if self.lst:
            self.log.debug(''.join(self.lst).rstrip('\n'))
            self.lst = []


def shutdown():
    _shutdownEvent.set()


def isShutdown():
    return _shutdownEvent.isSet()


def main():

    import PyLucene

    init(CONFIG_FILENAME)
    setup()

    # log some system info
    platform = sys.platform
    if 'win32' in sys.platform: platform += str(sys.getwindowsversion())

    log.info('-'*70)
    log.info('%s %s', config.APPLICATION_NAME, cfg.get('version','number'))
    log.info('Python %s', sys.version)
    log.info('  Platform %s', platform)
    log.info('  pwd: %s, defaultencoding: %s', os.getcwd(), sys.getdefaultencoding())
    log.info('PyLucene %s Lucene %s', PyLucene.VERSION, PyLucene.LUCENE_VERSION)

    # show index version
    import lucene_logic
    dbindex = cfg.getPath('archiveindex')
    reader = lucene_logic.Reader(pathname=dbindex)
    version = reader.getVersion()
    log.info('  Index version %s', version)

    proxyThread = threading.Thread(target=proxyMain, name='proxy')
    #proxyThread.setDaemon(True)
    proxyThread.start()

    adminThread = PyLucene.Thread(runnable(adminMain))
    #adminThread.setDaemon(True)
    adminThread.start()

#    time.sleep(3)
    indexThread = PyLucene.Thread(runnable(indexMain))
    indexThread.start()

    # main thread sleep
    _shutdownEvent.wait()

    # shutdown
    log.fatal('System shutting down.')
    indexThread.join()
    log.fatal('indexThread terminated.')
    adminThread.join()
    log.fatal('adminThread terminated.')
    proxyThread.join()
    log.fatal('proxyThread terminated.')
    log.fatal('End of main thread.')


#if __name__ == '__main__':
#    main()