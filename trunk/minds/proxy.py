""" MindSearch Main Program
"""

import logging
import os, sys
import threading

from minds.config import cfg
import app_httpserver
import config
import httpserver
import proxyhandler
import qmsg_processor
from minds.util import threadutil


### System Globals #####################################################

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
    port = cfg.getint('http.proxy_port')
    numThreads = cfg.getint('http.proxy_threads', 1)
    server_address = ('', port)
    global proxy_httpd
    proxy_httpd = httpserver.PooledHTTPServer(server_address, proxyhandler.ProxyHandler, numThreads)
    log.info('Proxy: %s', proxy_httpd.report_config())
    proxy_httpd.serve_forever()


admin_httpd = None

def adminMain():
    port = cfg.getint('http.admin_port')
    server_address = ('', port)
    global admin_httpd
    admin_httpd = httpserver.HTTPServer(server_address, app_httpserver.AppHTTPRequestHandler)
    log.info("Start admin on '%s' port %s" % server_address)
    app_httpserver.log.info('app_httpserver setup: docBase=%s',
        app_httpserver.AppHTTPRequestHandler.docBase)

    admin_httpd.serve_forever()


MAX_INDEX_INTERVAL = 24*60  # no more than 1 day

def indexMain():
    interval = cfg.getint('indexing.interval',3)
    interval = min(interval, MAX_INDEX_INTERVAL)
    log.info('Scheduled index thread to run every %s minutes' % interval)
    while not _shutdownEvent.wait(interval * 60):
        if _shutdownEvent.isSet():
            break
        try:
            qmsg_processor.backgroundIndexTask()
            # reset interval after a successful process
            interval = cfg.getint('indexing.interval',3)
            interval = min(interval, MAX_INDEX_INTERVAL)
        except:
            # log error, do not let the indexMain thread die
            import traceback
            traceback.print_exc()
            # expotential backoff
            interval *= 2
            interval = min(interval, MAX_INDEX_INTERVAL)
            log.info('Restart index thread in %s minutes' % interval)



########################################################################

def setup():
    """ module startup """
    cfg.setupPaths()
    setupLogging()


def setupLogging():
    # remove any bootstrap log handler installed
    rootlog = logging.getLogger()
    map(rootlog.removeHandler, rootlog.handlers)

    syslogpath = cfg.getpath('logs')/'system.log'
    hdlr = logging.handlers.RotatingFileHandler(syslogpath, 'a', 1100000, 4)
    formatter = logging.Formatter('%(asctime)s %(name)-10s - %(message)s')
    hdlr.setFormatter(formatter)

    # work around [python-Bugs-1314519] logging run into deadlock in some error handling situation
    # https://sourceforge.net/tracker/?func=detail&atid=105470&aid=1314519&group_id=5470
    hdlr.lock = threading.RLock()

    rootlog.addHandler(hdlr)
    rootlog.setLevel(logging.DEBUG)

    # redirect stdout and stderr to log
    sys.stdout = LogFileObj(logging.getLogger('stdout'))
    sys.stderr = LogFileObj(logging.getLogger('stderr'))
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
    log.fatal('System shutting down.')
    _shutdownEvent.set()


def isShutdown():
    return _shutdownEvent.isSet()


def main():
    import PyLucene

    setup()

    # log some system info
    platform = sys.platform
    if 'win32' in sys.platform: platform += str(sys.getwindowsversion())

    log.info('-'*70)
    log.info(cfg.application_name)
    log.info('Python %s', sys.version)
    log.info('  Platform %s', platform)
    log.info('  pwd: %s, defaultencoding: %s', os.getcwd(), sys.getdefaultencoding())
    log.info('PyLucene %s Lucene %s LOCK_DIR %s',
        PyLucene.VERSION, PyLucene.LUCENE_VERSION, PyLucene.FSDirectory.LOCK_DIR)

    # show index version
    import lucene_logic
    dbindex = cfg.getpath('archiveindex')
    reader = lucene_logic.Reader(pathname=dbindex)
    version = reader.getVersion()
    reader.close()
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
    indexThread.join()
    log.fatal('indexThread terminated.')
    adminThread.join()
    log.fatal('adminThread terminated.')
    proxyThread.join()
    log.fatal('proxyThread terminated.')
    log.fatal('End of main thread.')


if __name__ == '__main__':
    print >>sys.stderr, 'Please launch proxy from run.py'
    sys.exit(-1)