""" mhtml.py [-x] filename
"""

# TODO: (enh) gzip the archive


# Issue: 
# How to handle very large MIME Messages with the email package?
#   http://groups.google.com/group/comp.lang.python/browse_frm/thread/cfba0fad04af35c7/59c260c03abb8ff1?hl=en#59c260c03abb8ff1
# Handling large emails: DiskMessage and DiskFeedParser
#   http://mail.python.org/pipermail/email-sig/2004-October/000160.html


import cStringIO
import email
import sys
import threading

count = 0

def dir_mhtml(filename, extract=False):
    fp = file((filename),'rb')
    msg = email.message_from_file(fp)
    fp.close()
    global count
    count = 0
    print >>sys.stderr, '##', extract
    _walk(msg, extract)
    
    
def _walk(msg, extract, level=0):
    """A handy debugging aid"""
    global count
    tab = ' ' * (level * 4)
    print '%2d %s%s %s' % (count, tab, msg.get_content_type(), msg.get('content-location','-'))
    if msg.is_multipart():
        for subpart in msg.get_payload():
            _walk(subpart, level+1)
    else:
        if extract:
            fp = file('testdata/part%d' % count, 'wb')
            fp.write(msg.get_payload(decode=1))
            fp.close()
    count += 1


class FakeHTTPResponse(object):
    """ Turn an email.Message into HTTPResponse """
    
    def __init__(self, msg):
        self.msg = msg
        self.version = 11
        self.status = 200
        self.reason = 'OK'
        self.fp = cStringIO.StringIO(msg.get_payload(decode=1))
        
    def read(self, amt=None):
        if amt == None:
            return self.fp.read()
        else:
            return self.fp.read(amt)    
        
    def getheader(self, name, default=None):
        return self.msg.get(name, default)

    def getheaders(self):
        return self.msg.items()
        
        
class LoadedWebArchive(object):

    loadedObj = None
    loadingLock = threading.RLock()
    timer = None
    TIMEOUT = 60.0
    
    @staticmethod
    def load_fp(fp):
        obj = LoadedWebArchive(fp)
        LoadedWebArchive.load(obj)
        return obj


    @staticmethod
    def load(obj):
        LW = LoadedWebArchive
        LW.loadingLock.acquire()
        try:
            if LW.timer:
                LW.timer.cancel()
            LW.loadedObj = obj    
            LW.timer = threading.Timer(LW.TIMEOUT, LW.unload, [obj])
            LW.timer.start()
        finally:
            LW.loadingLock.release()


    @staticmethod
    def unload(oldObj=None):
        LW = LoadedWebArchive
        LW.loadingLock.acquire()
        try:
            if oldObj and LW.loadedObj != oldObj:
                # already replaced, do not unload
                return
            LW.loadedObj = None
            LW.timer = None
        finally:
            LW.loadingLock.release()


    @staticmethod
    def fetch_uri(uri):
        LW = LoadedWebArchive
        obj = LW.loadedObj
        # note: it is OK to if somebody unload LW.loadedObj at this point.
        if not obj:
            return None
        msg = obj.parts.get(uri,None)
        if not msg:
            return None
        return FakeHTTPResponse(msg)    


    def __init__(self, fp):
        self.msg = email.message_from_file(fp)
        self.parts = {}
        self.root_uri = None
        for part in self.iter_parts(self.msg):
            uri = part.get('content-location','')
            if not self.root_uri:
                self.root_uri = uri
            self.parts[uri] = part
                
                
    def iter_parts(self, msg):
        if msg.is_multipart():
            for subpart in msg.get_payload():
                for part in self.iter_parts(subpart):
                    yield part
        else:
            yield msg


    def __str__(self):
        s = ['root: %s (%s items)' % (self.root_uri, len(self.parts))]
        s.extend(self.parts.keys())
        return '\n  '.join(s)



def main(argv):
    if argv[1] == '-x':
        extract = True
        filename = argv[2]
    else:
        extract = False
        filename = argv[1]
        
    dir_mhtml(filename, extract)


if __name__ =='__main__':
    main(sys.argv)
        