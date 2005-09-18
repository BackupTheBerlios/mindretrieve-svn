"""
"""

import sys
import unittest

from minds.safe_config import cfg as testcfg
from minds import cachefile


class TestCacheFile(unittest.TestCase):

    FILE_BASE = 'testcache'

    def setUp(self):
        logpath = testcfg.getpath('logs')
        # check test path to avoid config goof
        # we will delete files!
        self.assert_('testlogs' in logpath)
        
        self.qlogpath = logpath/(self.FILE_BASE+'.qlog')
        self.mlogpath = logpath/(self.FILE_BASE+'.mlog')
        self.cleanup()


    def tearDown(self):
        self.cleanup()


    def cleanup(self):
        try: self.qlogpath.remove()
        except OSError: pass
        try: self.mlogpath.remove()
        except OSError: pass


    def test_write(self):
        c = cachefile.CacheFile(10)

        c.write('hello')
        self.assert_(not c.isOverflow())

        c.write('how are you?')
        self.assert_(c.isOverflow())

        self.assert_(not self.qlogpath.exists())
        self.assert_(not self.mlogpath.exists())

        c.write_qlog(self.FILE_BASE)
        self.assert_(self.qlogpath.exists())
        self.assert_(self.qlogpath.size==5)

        c.write_mlog(self.FILE_BASE)
        self.assert_(self.mlogpath.exists())
        self.assert_(self.mlogpath.size==5)


    def test_discard(self):
        c = cachefile.CacheFile(10)

        c.write('hello')
        self.assert_(not c.isOverflow())

        c.write('how are you?')
        self.assert_(c.isOverflow())

        c.discard()
        self.assert_(not self.qlogpath.exists())
        self.assert_(not self.mlogpath.exists())


if __name__ == '__main__':
    unittest.main()