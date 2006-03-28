import os.path
import unittest

import magic

testdir = 'lib/testdocs/test_magic/'


def guess(path):
    fp = file(path,'rb')
    try:
        return magic.guess_type(fp.read(256))
    finally:
        fp.close()


class TestMagic(unittest.TestCase):

    def test_empty_file(self):
        self.assertEqual(magic.guess_type(''), None)

    def test_partial_match0(self):
        self.assertEqual(magic.guess_type('GIF'), None)

    def test_partial_match1(self):
        self.assertEqual(magic.guess_type('GIF123456789'), None)

    def test_partial_mask_match0(self):
        self.assertEqual(magic.guess_type('\x00'), None)

    def test_partial_mask_match1(self):
        self.assertEqual(magic.guess_type('\x00123456789'), None)

    def test_gif(self):
        self.assertEqual(guess(testdir + 'PythonPowered.gif'), 'image/gif')

    def test_jpeg(self):
        self.assertEqual(guess(testdir + 'penguin100.jpg'), 'image/jpeg')

    def test_png(self):
        self.assertEqual(guess(testdir + 'penguin50.png'), 'image/png')

    def test_ico(self):
        self.assertEqual(guess(testdir + 'pycon.ico'), 'image/vnd.microsoft.icon')

    def test_utf8(self):
        self.assertEqual(guess(testdir + 'hello.utf8'), None)

    def test_uft16(self):
        self.assertEqual(guess(testdir + 'hello.utf16'), None)

    def test_zip(self):
        self.assertEqual(guess(testdir + 'hello.zip'), None)

    def test_text_html(self):
        self.assertEqual(guess(testdir + 'sample.html'), None)


if __name__ == '__main__':
    unittest.main()