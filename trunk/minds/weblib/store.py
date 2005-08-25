""" Define load() and save() to as the system persistence method.
"""
# 2005-08-24 is this layer really useful?

import logging
import sys

from minds.weblib import minds_lib
from minds.weblib import opera_lib

log = logging.getLogger('weblib')

def_store = minds_lib

WEBLIB_FILENAME = 'weblib.dat'

OPERA_FILENAME = 'opera6.adr'
MINDS_FILENAME = 'weblib.dat'


def _run_close(fp, func, *args):
    """ close fp after running func """
    try:
        return func(*args)
    finally:
        fp.close()       


def load(filename=None):
    filename = filename or WEBLIB_FILENAME
    fp = file(filename,'rb')
    wlib = _run_close(fp, def_store.load, fp)
    log.debug('Loaded %s items:%s,%s', filename, len(wlib.tags), len(wlib.webpages))
    return wlib

    
def save(wlib, filename=None):
    filename = filename or WEBLIB_FILENAME
    fp = file(filename,'wb')            
    _run_close(fp, def_store.save, fp, wlib)
    log.debug('Saved %s items:%s,%s', filename, len(wlib.tags), len(wlib.webpages))


def load_opera(filename=None):
    filename = filename or OPERA_FILENAME
    fp = file(filename,'rb')
    wlib = _run_close(fp, opera_lib.load, fp)
    log.debug('Loaded %s items:%s,%s', filename, len(wlib.tags), len(wlib.webpages))
    return wlib

# ----------------------------------------------------------------------
wlib_instance = None

def getMainBm():
    global wlib_instance
    if not wlib_instance:
        wlib_instance = load()
    return wlib_instance


def useMainBm(pathname):
    """ use pathname instead of default filename (testing only?) """
    global WEBLIB_FILENAME
    WEBLIB_FILENAME = pathname
    global wlib_instance
    wlib_instance = load(WEBLIB_FILENAME)
    
    
# ----------------------------------------------------------------------
def main(argv):
    from minds.weblib import minds045_lib
    
    wlib = minds_lib.load(file(WEBLIB_FILENAME+'X','rb'))
    minds_lib.save(file(WEBLIB_FILENAME+'Y','wb'),wlib)
    return
    
    wlib = minds045_lib.load(file(WEBLIB_FILENAME,'rb'))
    minds_lib.save(file(WEBLIB_FILENAME+'X','wb'),wlib)
    return
    # put the script here
    wlib = load_opera()
    save(wlib)


if __name__ =='__main__':
    main(sys.argv)
        