""" Define load() and save() to as the system persistence method.
"""

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


def load(filename=WEBLIB_FILENAME ):
    fp = file(filename,'rb')
    wlib = _run_close(fp, def_store.load, fp)
    log.debug('Loaded %s items:%s,%s', filename, len(wlib.tags), len(wlib.webpages))
    return wlib

    
def save(wlib, filename=WEBLIB_FILENAME):
    fp = file(filename,'wb')            
    _run_close(fp, def_store.save, fp, wlib)
    log.debug('Saved %s items:%s,%s', filename, len(wlib.tags), len(wlib.webpages))


def load_opera(filename=OPERA_FILENAME):
    fp = file(filename,'rb')
    wlib = _run_close(fp, opera_lib.load, fp)
    log.debug('Loaded %s items:%s,%s', filename, len(wlib.tags), len(wlib.webpages))
    return wlib

    
def main(argv):
    # put the script here
    wlib = load_opera()
    save(wlib)


if __name__ =='__main__':
    main(sys.argv)
        