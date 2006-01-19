'''Utility to read and write multiple block of data into a single file.

Multi Block File Format
-----------------------

A file contain consecutive blocks. Each block start with 24 bytes header
with the body length in ASCII digits, follows by a filler line. The body
start from byte 24 from the beginning of the block and ended by
\r\n\r\n. This could be immediately followed by the next block.

  nnn\r\n       Content length of body 1
  SP * \r\n     Filler line
  body1         body 1
  \r\n
  \r\n

  nnn\r\n       Content length of body 2
  SP * \r\n     Filler line
  body2         body 2
  \r\n
  \r\n

  ...and so on

How many digits should we allocate for content length?

  1MB approx 1e6
  1GB approx 1e9
  1TB approx 1e12

By allocating 24 bytes for the block header, it allows content length of
20 digit (plus 4 for \r\n\r\n). In reality the content length is also
limited by Python's integer size (32bit?).

'''

# TODO: change API to have a container object with __iter__() instead of directly instantiating MbReader and MbWriter?

import os

INIT_HEADER = '0\r\n' + ' '*19 + '\r\n'
HEADER_LENGTH = 24
assert len(INIT_HEADER) == HEADER_LENGTH


class MbWriter(object):

    ''' File-like object for writing a block to the supplied
    base file object. Must call complete() after finished writing the
    block.

    For example:
    >>> fp = file('test.dat','wb')
    >>> fout = MbWriter(fp)
    >>> fout.write("line1\n")
    >>> fout.write("line2")
    >>> fout.complete()
    >>> fout.clen
    11
    >>> # repeat for other blocks
    ...
    >>> fp.close()

    fp should support seek(), tell() and mode.
    Output start from fp's current position.
    '''

    def __init__(self,fp):
        ''' Supply the base file. '''
        self.fp = fp
        self.closed = False
        if hasattr(fp,'mode') and fp.mode != 'wb':
            raise IOError, 'only support mode "wb"'

        self.clen = 0
        self.init_pos = fp.tell()
        fp.write(INIT_HEADER)

    def write(self,str):
        self.fp.write(str)
        self.clen += len(str)

    def writelines(self,sequence):
        raise IOError, 'writelines() not supported'

    def complete(self):
        if self.closed: return
        self.closed = True

        self.fp.write('\r\n\r\n')

        slen = str(self.clen)
        # integrity check
        if len(slen)+4 > HEADER_LENGTH:
            raise IOError, 'Content length too large: [%s]' % slen

        endpos = self.fp.tell()
        self.fp.seek(self.init_pos)
        self.fp.write(slen)
        self.fp.write('\r\n')
        self.fp.seek(endpos)

    def close(self):
        self.complete()



class MbReader(object):

    ''' File-like object for reading a block from the supplied base file
    object. Must call complete() after finished reading a block in order
    to position to next block.

    For example:
    >>> fp = file('test.dat','rb')
    >>> fin = MbReader(fp)
    >>> fin.read()
    'line1\nline2'
    >>> fin.complete()
    >>> # repeat for other blocks
    ...
    >>> fp.close()

    fp should support seek(), tell() and mode.
    fp's should be positioned at block's start.
    '''

    #BUFSIZE = 8192
    #def __init__(self, fp, bufsize=MbReader.BUFSIZE):
    def __init__(self, fp, bufsize=8192):

        self.fp = fp
        self.bufsize = bufsize
        self.closed = False

        if hasattr(fp,'mode') and fp.mode != 'rb':
            raise IOError, 'only support mode "rb"'

        # read header for clen
        blockpos0 = fp.tell()
        line = fp.readline()
        try:
            self.clen = int(line.rstrip('\r\n'))
        except :
            raise IOError, 'Unknown content length: ' + line
        if self.clen < 0:
            raise IOError, 'Negative content length: ' + line
        filler = fp.readline()
        if filler.strip():
            raise IOError, 'Invalid or missing filler line %s' % filler

        # position relative to beginning of data in this block
        self.start_pos = fp.tell()
        self.remain_bytes = self.clen

        header_len = self.start_pos-blockpos0
        if header_len > HEADER_LENGTH:
            raise IOError, 'Invalid start data position (block0=%s,start=%s)' % (blockpos0, self.start_pos)
        # it is also questionable if header_len < HEADER_LENGTH. But we
        # should be more lenient when reading. In case the log file is
        # edited and has trailing spaces truncated, it should still be opened.


    def read(self,size=-1):
        if self.remain_bytes <= 0 or self.closed:
            return ''
        if size == -1:
            size = self.bufsize
        size = min(size, self.remain_bytes)

        data = self.fp.read(size)
        self.remain_bytes -= len(data)

        return data


    def readline(self,size=-1):
        if self.remain_bytes <= 0 or self.closed:
            return ''
        if size < 0:
            size = self.remain_bytes
        else:
            size = min(size, self.remain_bytes)

        data = self.fp.readline(size)

        # note mode must be 'rb' in Windows or the len here would be wrong
        self.remain_bytes -= len(data)

        return data


    def readlines(self,sizehint=-1):
        raise IOError, 'readlines() not supported'


    def __iter__(self):
        return self


    def next(self):
        data = self.readline()
        if not data: raise StopIteration
        return data


    def complete(self):
        if self.closed: return
        self.closed = True

        # flush remain_bytes
        if self.remain_bytes > 0:
            self.fp.seek(self.remain_bytes, 1)

        # check block end marker
        data = self.fp.read(4)
        self.remain_bytes = 0
        if data != '\r\n\r\n':
            raise IOError, 'End of block marker \\r\\n\\r\\n not found'


    def close(self):
        self.complete()


    # Note: seek() and tell() below are added so that it can be used with the gzip module

    def tell(self):
        return self.fp.tell() - self.start_pos

    def seek(self, offset, whence=0):
        if whence == 1:
            # seek relative to current
            current = self.clen - self.remain_bytes
            offset += current
        elif whence == 2:
            # seek relative to EOF
            offset += self.clen

        # bound the offset
        if offset < 0:
            offset = 0
        elif offset > self.clen:
            offset = self.clen

        # seek absolute (with respect to start of data)
        self.fp.seek(self.start_pos + offset)
        self.remain_bytes = self.clen - offset


# ----------------------------------------------------------------------
# testing
# ----------------------------------------------------------------------

import StringIO, unittest

class TestReaderWriter(unittest.TestCase):

  TEST_FILENAME = 'test.dat'

  def _write(self, fp, *data):
    ''' test write() with any number of chunks '''
    fout = MbWriter(fp)
    for d in data:
        fout.write(d)
    fout.complete()


  def _read_test(self, label, fin, data, content_expected):
    self._printBlock(label, fin.clen, data)
    self.assertEqual( data, content_expected)
    self.assertEqual( fin.clen, len(data))


  def _printBlock(self, label, length, data):
      print '\n%s clen=%d len(data)=%d [[%s]]' % (label, length, len(data), data.replace('\n', '\\n'))


  def _makeMbFp(self, header_format, content):
    """ A helper to make multiblockfile for testing. Assume data has 2 dight length. """
    header = header_format % len(content)
    data = header + content+ '\r\n'
    #print '[%s]' % data
    return StringIO.StringIO(data)


  def testFillerline(self):

    # controlled test
    fp = self._makeMbFp('%s\r\n                  \r\n', 'This is the begin of data. It has valid filler line.\r\n')
    self.assert_(MbReader(fp).read().endswith('filler line.\r\n'))

    # truncated is OK
    fp = self._makeMbFp('%s\r\n\r\n', 'This is the begin of data. It has truncated filler line.\r\n')
    self.assert_(MbReader(fp).read().find('truncated filler line.') > 0)

    # perhaps a missing filler line
    fp = self._makeMbFp('%s\r\n_bad filler_\r\n','This is the begin of data. It has an invalid filler line.\r\n')
    self.assertRaises(IOError, MbReader, fp)

    # 24 filler chars max
    fp = self._makeMbFp('%s\r\n                   \r\n', 'This is the begin of data. It has a too long filler line.\r\n')
    self.assertRaises(IOError, MbReader, fp)


  def testReadWrite(self):

    # note: this is built as one big test because besides testing
    #   individual API, it also tests the ability to read through a
    #   series of blocks in the test file.

    print '\n@testReadWrite'

    content1 = 'Message 1 has\n3 lines\nand ends without line break.'
    content2 = 'Message 2 has\n3 lines\nand ends with a line break.\n'
    content3 = 'Message 3 has 3 lines  \n\nand ends without line break.'
    content4 = 'Message 4 has  \n3 lines\nand ends with a line break.\n'
    content5 = 'Message 5 has 3 lines  \n\nand ends without line break.'
    content6 = 'Message 6 has  \n3 lines\nand ends with a line break.\n'
    content8 = 'Message 8 has  \n2 lines and ends wit a line break.\n'
    content9 = 'Message 9 has  \n2 lines and ends without line break.'


    # Output test
    fp = file(self.TEST_FILENAME, 'wb')
    self._write(fp, content1)
    self._write(fp, content2)
    self._write(fp, content3[:10], content3[10:20], content3[20:])
    self._write(fp, content4[:20], content4[20:30], content4[30:])
    self._write(fp, content5)
    self._write(fp, content6)
    self._write(fp)              # VERY IMPORTANT: test read/write with empty content!
    self._write(fp, content8)
    self._write(fp, content9)
    fp.close()


    # Input test:
    #   1-6:
    #       3 styles to read [read(), readline(), iter()]
    #       2 ways to end a message (with or without linebreak)
    #   7:  test message with empty content
    #   8:  test partial read
    #   9:  test read(size)
    #   10: test block positioning

    fp = file(self.TEST_FILENAME, 'rb')

    fin = MbReader(fp)
    data = fin.read()
    self._read_test('Block1', fin, data, content1)
    fin.complete()

    fin = MbReader(fp)
    data = fin.read()
    self._read_test('Block2', fin, data, content2)
    fin.complete()

    fin = MbReader(fp)
    data = ''
    while True:
        line = fin.readline()
        if not line: break
        data += line
    self._read_test('Block3', fin, data, content3)
    fin.complete()

    fin = MbReader(fp)
    data = ''
    while True:
        line = fin.readline()
        if not line: break
        data += line
    self._read_test('Block4', fin, data, content4)
    fin.complete()

    fin = MbReader(fp)
    data = ''
    for line in fin:
        data += line
    self._read_test('Block5', fin, data, content5)
    fin.complete()

    fin = MbReader(fp)
    data = ''
    for line in fin:
        data += line
    self._read_test('Block6', fin, data, content6)
    fin.complete()

    fin = MbReader(fp)
    data = fin.read()
    self._read_test('Block_nil', fin, data, '')
    fin.complete()

    fin = MbReader(fp)
    data = fin.read(22)
    self._printBlock('Block8 partial', fin.clen, data)
    self.assertEqual( data, content8[:22])
    # ignore remaining data not read
    fin.complete()

    fin = MbReader(fp)
    data = fin.read(25)
    data += fin.read(100)
    self._read_test('Block9', fin, data, content9)
    fin.complete()

    # test reading block 9 by skipping first 8 blocks
    fp.seek(0)                  # reposition to the beginning
    for i in range(8):
        MbReader(fp).complete() # skip first 8 blocks
    fin = MbReader(fp)          # should position at block 9
    data = fin.read()
    self._read_test('Block9', fin, data, content9)
    fin.complete()

    fp.close()
    os.remove(self.TEST_FILENAME)


  def testTellNSeek(self):
    print '\n@testTellNSeek'

    # Build output file
    block1 = 'This is block 1'
    block2 = ''
    block3 = '0123456789'
    fp = file(self.TEST_FILENAME, 'wb')
    self._write(fp, block1)
    self._write(fp, block2)
    self._write(fp, block3)
    fp.close()

    fp = file(self.TEST_FILENAME, 'rb')

    # skip block 1
    MbReader(fp).complete()

    # test empty block 2
    fin = MbReader(fp)
    self.assertEqual(fin.tell(), 0)
    fin.seek(5)
    self.assertEqual(fin.tell(), 0)
    self.assertEqual(fin.read(1), '')
    fin.complete()

    # test block 3
    fin = MbReader(fp)
    self.assertEqual(fin.tell(), 0)

    # seek absolute
    fin.seek(5)
    self.assertEqual(fin.tell(), 5)
    self.assertEqual(fin.read(1), '5')

    # seek relative to current
    fin.seek(-2,1)
    self.assertEqual(fin.tell(), 4)
    self.assertEqual(fin.read(1), '4')

    fin.seek(3,1)
    self.assertEqual(fin.tell(), 8)
    self.assertEqual(fin.read(1), '8')

    fin.seek(99,1)
    self.assertEqual(fin.tell(), 10)
    self.assertEqual(fin.read(1), '')

    fin.seek(-99,1)
    self.assertEqual(fin.tell(), 0)
    self.assertEqual(fin.read(1), '0')

    # seek absolute
    fin.seek(999)
    self.assertEqual(fin.tell(), 10)
    self.assertEqual(fin.read(1), '')

    # seek relative to EOF
    fin.seek(-3, 2)
    self.assertEqual(fin.tell(), 7)
    self.assertEqual(fin.read(1), '7')

    fin.seek(2, 2)
    self.assertEqual(fin.tell(), 10)
    self.assertEqual(fin.read(1), '')

    fp.close()
    os.remove(self.TEST_FILENAME)


if __name__ == '__main__':
    unittest.main()