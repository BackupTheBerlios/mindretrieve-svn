"""
"""

import os, os.path, sys
import unittest

from config_help import cfg
from minds import cachefile



class TestCacheFile(unittest.TestCase):

    FILE1 = 'testcache'

    def setUp(self):
        self.pathname = os.path.join(cfg.getPath('logs'), self.FILE1)
        self.cleanup()


    def tearDown(self):
        self.cleanup()


    def cleanup(self):
        # hardcode path to avoid deleting real data in config goof
        try: os.remove('testlogs/' + self.FILE1 + '.mlog')
        except OSError: pass
        try: os.remove('testlogs/' + self.FILE1 + '.qlog')
        except OSError: pass


    def test_write(self):

        c = cachefile.CacheFile(10)

        c.write('hello')
        self.assert_(not c.isOverflow())

        c.write('how are you?')
        self.assert_(c.isOverflow())

        self.assert_(not os.path.exists(self.pathname+'.qlog'))
        self.assert_(not os.path.exists(self.pathname+'.mlog'))

        c.write_qlog(self.FILE1)
        self.assert_(os.path.exists(self.pathname+'.qlog'))
        self.assert_(os.path.getsize(self.pathname+'.qlog'),5)

        c.write_mlog(self.FILE1)
        self.assert_(os.path.exists(self.pathname+'.mlog'))
        self.assert_(os.path.getsize(self.pathname+'.mlog'),5)


    def test_discard(self):

        c = cachefile.CacheFile(10)

        c.write('hello')
        self.assert_(not c.isOverflow())

        c.write('how are you?')
        self.assert_(c.isOverflow())

        c.discard()
        self.assert_(not os.path.exists(self.pathname+'.qlog'))
        self.assert_(not os.path.exists(self.pathname+'.mlog'))


if __name__ == '__main__':
    unittest.main()