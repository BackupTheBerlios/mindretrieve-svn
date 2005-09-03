#import ConfigParser
#import logging, logging.handlers
#import os
#import os.path
#import StringIO
import sys
import unittest

from minds import config

TEST_FILENAME = 'config.ini'

class TestConfig(unittest.TestCase):

  def setUp(self):
    self.cfg = config.Config()

  def tearDown(self):
    pass

  def testConfig(self):
    self.cfg.load(TEST_FILENAME)
    print str(self.cfg)
    self.assert_( self.cfg.get('version.created').find('2005') >= 0)


  def testSetupPaths(self):
    self.cfg.load(TEST_FILENAME)
    self.cfg.setupPaths()                # this will have side effect on the FS!


  def testDefault(self):
    self.cfg.load(TEST_FILENAME)

    self.assertNotEqual( self.cfg.get('version.created','X'), 'X')           # not using default

    self.assertEqual( self.cfg.get('version.nonexist', 'default'), 'default')
    self.assertEqual( self.cfg.get('version.nonexist', ''       ), '')       # Test out default of ''

    self.assertEqual( self.cfg.getint('version.nonexist', 1), 1)
    self.assertEqual( self.cfg.getint('version.nonexist', 0), 0)             # Test out default of 0

    self.assertEqual( self.cfg.getboolean('version.nonexist', True ), True )
    self.assertEqual( self.cfg.getboolean('version.nonexist', False), False) # Test out default of False


if __name__ == '__main__':
    unittest.main()