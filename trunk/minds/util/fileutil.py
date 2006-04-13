"""Utility to create file like objects
"""

import os
import StringIO

def listdir(path, name_filter=None):
    """ A custom version of os.listdir that takes regex filter. """

    # note 2005-09-18: path.listdir() is not compatible with
    # os.listdir() because it concat basedir with files. Arguably useful
    # in many situation but requires more code change for us.
    if filter:
        return filter(name_filter.match, os.listdir(path))
    else:
        return os.listdir(path)


class aStringIO(StringIO.StringIO):
    """ Some customerizations the StringIO module to provides the 'closed' attribute """

    def close(self):
        """ override default behaviour of freeing memory """
        pass

    #closed = property(self.getClose)
    #def __getattr__(self,name):
    #    if name=='closed':
    #        return self.close()
    #    else:
    #        raise AttributeError
    #


class FileFilter(object):
    """ FileFilter contains some other file as the backing data source """
    def __init__(self,fp):
        self.fp = fp

    def flush(self):
        self.fp.flush()

    def read(self,*args):
        return self.fp.read(*args)

    def readline(self,*args):
        return self.fp.readline(*args)

    def readlines(self,*args):
        return self.fp.readlines(*args)

    def write(self,str):
        self.fp.write(str)

    def writelines(self,sequence):
        self.fp.writelines(sequence)

    def __iter__(self):
        return self

    def next(self):
        data = self.readline()
        if not data: raise StopIteration
        return data

    def close(self):
        self.fp.close()

    def __getattr__(self, name):
        return getattr(self.fp, name)



class RecordFile(FileFilter):
    """ record data read from fp in fpRec """

    def __init__(self, fp, fpRec):
        FileFilter.__init__(self, fp)
        self.fpRec = fpRec

    def flush(self):
        FileFilter.flush(self)
        self.fpRec.flush()

    def read(self,*args):
        data = FileFilter.read(self, *args)
        if data: self.fpRec.write(data)
        return data

    def readline(self,*args):
        data = FileFilter.readline(self, *args)
        if data: self.fpRec.write(data)
        return data

    def readlines(self,*args):
        data = FileFilter.readlines(self, *args)
        if data: self.fpRec.writelines(data)
        return data

    def close(self):
        FileFilter.close(self)
        self.fpRec.close()



class BoundedFile(FileFilter):
    """ An output file those size is bounded by a cap. Node if the base
        file is text mode in Windows, the final size may exceed the cap
        because \n is expanded to \r\n.
    """
    def __init__(self, fp, maxsize):
        super(BoundedFile, self).__init__(fp)
        self.maxsize = maxsize
        self.cursize = 0
        self.overflow = False

    def isOverflow(self):
        return self.overflow

    def write(self,str):
        if self.overflow:
            return
        if self.cursize+len(str) > self.maxsize:
            self.overflow = True
            return
        self.cursize += len(str)
        self.fp.write(str)

    def writelines(self,sequence):
        for line in sequence:
            self.write(line)

    def __getattr__(self, attrib):
        """ Delegates other attributes to the underlaying file obj """

        # Simple delegation does not support new style class' special methods
        # See ASPN Generalized delegates and proxies at
        #   http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/252151
        return getattr(self.fp, attrib)



class FileSocket:
    """ A virtual socket backed by file objcet """

    def __init__(self, fin, fout=None):
        self.fin = fin
        self.fout = fout

    def makefile(self, mode='rb', bufsize=0):
        if mode == 'rb': return self.fin
        if mode == 'wb': return self.fout
        raise IOError('only support mode="rb"')

    def send(self, data, flags=0):
        self.fout.write(data)

    def close(self):
        ''' a reasonable action '''
        self.fin.close()
        self.fout.close()


def shift_files(files):
    """
    Rename files f[0] -> f[1] -> ... -> f[-1]

    if f[i] does not exist, it will be ignored.
    f[-1] would be rolled out to make way for f[0:-1]
    """
    n = len(files)
    if not n: returns   # noop
    assert n != 1       # we would alert you for this

    try:
        # TODO: for unix, we can do rename atomically without removing the dest file first
        os.remove(files[-1])    # remove if exist
    except OSError:
        pass

    for i in xrange(n-1,0,-1):
        dest = files[i]
        src = files[i-1]
        if os.path.exists(src):
            # dest should already be vacated
            os.rename(src,dest)

