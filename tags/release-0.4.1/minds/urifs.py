""" URI File System
"""

# todoc: host:80 is different from host so is ip

# host:80 is normalized to host
# ip in url is not normalized

# use UTF-8?
# when to urldecode?




import os.path
import urlparse
import sys

from minds.config import cfg

###dataBase = './data'
DOMAINFILE = 'domain.txt'
domainMap = {}


class UriResources(object):
    def __init__(self, uri):
        self.uri = uri
    def close(self):
        pass


def openDomainFp(*args):
    """ open the domain data file """
    path = cfg.getPath('logs')
    filename = os.path.join(path,DOMAINFILE)
    return file(filename,*args)


def open(uri, date=None, ctype='', clen=0):
    host, path = parse(uri)
    #print "###",host,path,uri
    if not domainMap.has_key(host):
        domainMap[host] = 1
        log("Adding domain: " + host)
        #fp = file(os.path.join(dataBase,DOMAINFILE),'a')
        fp = openDomainFp('a')
        fp.write(host)
        fp.write('\n')
        fp.flush()
        fp.close()



def parse(uri):
    """ parse URI into host and path parts.
        Normalize host to lower case and remove ':80' if present
    """

    scheme, netloc, path, query, frag = urlparse.urlsplit(uri, allow_fragments=False)
    if '@' in netloc:
        raise IOError('userinfo not allowed: ' + netloc)
    # normalize 'host:80' into 'host'
    if netloc[-3:] == ':80':
        netloc = netloc[:-3]
    if query:
        path += '?' + query

    return netloc.lower(), path


def log(msg):
    sys.stdout.write(msg)
    sys.stdout.write('\n')

def init():
    global domainMap
    domainMap = {}
    ###path = proxy.cfg.get('path','logs','.')
    ###fp = file(os.path.join(path,DOMAINFILE),'r')
    for line in openDomainFp('a+'):
        # validation (lower case, etc)
        line = line.rstrip('\n')
        domainMap[line] = 1
    log("domains defined: %d" % len(domainMap))


### testing ############################################################
###~~import proxy

def test():
    ###~~~proxy.init('test_config.ini')
    init()
    open("http://abc.com/def")
    open("http://abc.org/def")
    open("http://abc.com/")

if __name__ == '__main__':
    test()