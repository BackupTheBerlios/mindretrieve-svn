"""Usage: domain_filter.py
"""

import string
import sys

from minds.config import cfg
from minds.util import httputil


g_exdm = None


def load():
    """ Reload g_exdm from config """
    exdms = []
    for i in range(5):
        exdm_str = cfg.get('filter.domain.%s' % i, '')   # get domain.0 - domain.4
        lst = exdm_str.split(',')                           # parse ',' separated str
        exdms += filter(None, map(string.strip, lst))       # strip spaces, drop ''

    global g_exdm
    g_exdm = exdms  # atomic switch over


def match(uri):
    """ Return the filter domain that match the uri. None means not filtered. """

    if g_exdm == None:
        load()

    scheme, userinfo, host, path, query, frag = httputil.urlsplit(uri)
    for ex in g_exdm:
        if ex[0] == '.':
            if host.endswith(ex):
                return ex
        else:
            if host == ex:
                return ex
    return None


def main(argv):
    pass

if __name__ == '__main__':
    main(sys.argv)