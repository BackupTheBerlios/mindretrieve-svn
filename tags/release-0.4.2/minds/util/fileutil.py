"""Utility to create file like objects
"""

import StringIO

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





### Testing ############################################################

import unittest

class TestBoundedFile(unittest.TestCase):

  def test_boundedFile(self):
    print '\n@test_boundedFile'
    buf = StringIO.StringIO()
    bfp = BoundedFile(buf, 10)

    bfp.write('12345')
    self.assert_(not bfp.isOverflow())
    self.assertEqual(len(buf.getvalue()), 5)

    bfp.write('678')
    self.assert_(not bfp.isOverflow())
    self.assertEqual(len(buf.getvalue()), 8)

    bfp.write('90ab')
    self.assert_(bfp.isOverflow())
    self.assertEqual(len(buf.getvalue()), 8)

    # although bfp is still 2 characters below maxsize
    # make sure once it is overflowed you cannot write anymore
    bfp.write('c')
    self.assert_(bfp.isOverflow())
    self.assertEqual(len(buf.getvalue()), 8)


  def test_boundedFile1(self):
    print '\n@test_boundedFile1'
    buf = StringIO.StringIO()
    bfp = BoundedFile(buf, 10)

    # check boundary condition when cursize == maxsize
    bfp.write('1234567890')
    self.assert_(not bfp.isOverflow())
    self.assertEqual(len(buf.getvalue()), 10)

    bfp.write('a')
    self.assert_(bfp.isOverflow())
    self.assertEqual(len(buf.getvalue()), 10)


  def test_boundedFileDelegation(self):
    print '\n@test_boundedFileDelegation'
    buf = StringIO.StringIO()
    bfp = BoundedFile(buf, 10)

    bfp.write('1234567890')
    self.assertEqual(bfp.getvalue(), '1234567890')




class TestFileUtil(unittest.TestCase):

  def test_RecordFile(self):
    print '\n@test_RecordFile'
    f1 = StringIO.StringIO("""line1\r\nline2\r\nline3\n""")
    rec = StringIO.StringIO()
    for i, line in enumerate(RecordFile(f1,rec)):
        print 'line %d: [%s]' % (i, line)
    self.assertEqual(f1.getvalue(), rec.getvalue())

if __name__ == '__main__':
    unittest.main()