import sys
import unittest

from minds.safe_config import cfg

class TestConfig(unittest.TestCase):

 def setUp(self):
    self.cfg = cfg

# def tearDown(self):
#    pass


 def testDefault(self):
    self.assertNotEqual( self.cfg.get('version.created','X'), 'X')           # not using default

    self.assertEqual( self.cfg.get('version.nonexist', 'default'), 'default')
    self.assertEqual( self.cfg.get('version.nonexist', ''       ), '')       # Test out default of ''

    self.assertEqual( self.cfg.getint('version.nonexist', 1), 1)
    self.assertEqual( self.cfg.getint('version.nonexist', 0), 0)             # Test out default of 0

    self.assertEqual( self.cfg.getboolean('version.nonexist', True ), True )
    self.assertEqual( self.cfg.getboolean('version.nonexist', False), False) # Test out default of False


 def testGet(self):
    self.assert_( self.cfg.get('version.created').find('2005') >= 0)


 def testGetPref(self):
    self.fail('need test')  


 def testGetPath(self):
    datapath = cfg.getpath('data')
    # Test
    # a. data is a path object.
    # b. datapath exists (because implicit call to setupPaths()
    self.assert_(datapath.exists())


 def testUpdate_pref(self):
    self.fail('need test')  


 def testStr(self):   
    print str(self.cfg)


 def testSafeConfig(self):
    # make sure we are using safe test config
    
    keys = [n for n,v in cfg.cparser.items('path')]
    # take these items outside of test
    keys.remove('docbase')    
    keys.remove('testdoc')    
    # check that the above code do what we want
    self.assert_('data' in keys)
    self.assert_('logs' in keys)
    self.assert_('weblibsnapshot' in keys)
    self.assert_('archiveindex' in keys)
    
    for name in keys:
        self.assert_('test' in cfg.getpath(name))

    # we get test path even if we import from config
    from minds.config import cfg as config_cfg
    for name in keys:
        self.assert_('test' in config_cfg.getpath(name))



if __name__ == '__main__':
    unittest.main()