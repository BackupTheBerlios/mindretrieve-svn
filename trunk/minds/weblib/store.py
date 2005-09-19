""" Define load() and save() to as the system persistence method.
"""
# 2005-08-24 is this layer really useful?

import logging
import sys

from minds.config import cfg
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


def _open(filename, mode):
    """ open filename relative to weblib directory """
    return (cfg.getpath('weblib')/filename).open(mode)
    
    
def load(filename=None):
    # note: WEBLIB_FILENAME is not default parameter because it may change
    fp = _open(filename or WEBLIB_FILENAME,'rb')
    wlib = _run_close(fp, def_store.load, fp)
    log.debug('Loaded %s items:%s,%s', filename, len(wlib.tags), len(wlib.webpages))
    return wlib

    
def save(wlib, filename=None):
    # note: WEBLIB_FILENAME is not default parameter because it may change
    fp = _open(filename or WEBLIB_FILENAME,'wb')
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
    if wlib_instance:
        return wlib_instance
    return reloadMainBm()


def reloadMainBm():
    global wlib_instance
    wlib_instance = load()
#    wlib_instance.init_index()
    return wlib_instance
    
    
# ----------------------------------------------------------------------

# adhoc cmdline tool. May not work
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
        