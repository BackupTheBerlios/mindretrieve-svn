import os, os.path
import sys
import unittest

from minds.safe_config import cfg as testcfg
from minds import base_config

testpath = testcfg.getpath('data')


class TestConfig(unittest.TestCase):

 def setUp(self):
    self.cfg = base_config.Config()
    self.cfg.load_test_config()
    assert 'test' in testpath


# def tearDown(self):
#    pass


 def test_get(self):
    year = self.cfg.get('_system.created')[:4]
    year = int(year)
    self.assert_(2000 < year < 3000)


 def test_getdefault(self):
    self.assertNotEqual( self.cfg.get('_system.created','X'), 'X')           # not using default

    self.assertEqual( self.cfg.get('_system.nonexist', 'default'), 'default')
    self.assertEqual( self.cfg.get('_system.nonexist', ''       ), '')       # Test out default of ''

    self.assertEqual( self.cfg.getint('_system.nonexist', 1), 1)
    self.assertEqual( self.cfg.getint('_system.nonexist', 0), 0)             # Test out default of 0

    self.assertEqual( self.cfg.getboolean('_system.nonexist', True ), True )
    self.assertEqual( self.cfg.getboolean('_system.nonexist', False), False) # Test out default of False


 def test_get_notexist(self):
    self.assertRaises(KeyError, self.cfg.get, 'xx.yy')


 def test_getint(self):
    self.cfg.set('xx.yy','123')
    self.assertEqual(self.cfg.getint('xx.yy', 7), 123)
    self.assertEqual(self.cfg.getint('xx.not_exist',7), 7)

    self.cfg.set('xx.yy','zz')
    self.assertEqual(self.cfg.getint('xx.yy', 7), 7)


 def test_getboolean(self):
    self.cfg.set('xx.yy','1')
    self.assertEqual(self.cfg.getboolean('xx.yy'), True)
    self.assertEqual(self.cfg.getboolean('xx.not_exist',True), True)

    self.cfg.set('xx.yy','0')
    self.assertEqual(self.cfg.getboolean('xx.yy'), False)

    # Alas, this is not valid according to ConfigParser.getboolean()
    self.cfg.set('xx.yy','')
    self.assertEqual(self.cfg.getboolean('xx.yy', True), True)


 def test_getpath(self):
    datapath = self.cfg.getpath('data')
    # Test
    # a. data is a path object.
    # b. datapath exists (because implicit call to setupPaths()
    self.assert_(datapath.exists())


 def test_set(self):
    self.cfg.set('xx.yy','zz')
    self.assertEqual(self.cfg.get('xx.yy'),'zz')


 def test_save(self):
    outfile = testpath / 'config.ini'
    try:
        outfile.remove()
    except OSError:
        pass
    self.cfg.config_path = outfile

    self.cfg.set('xx.yy','zz')
    self.cfg.save()

    text = file(outfile,'rb').read()
    self.assert_(base_config.VERSION in text)
    self.assert_(base_config.CREATED in text)
    self.assert_('updated' in text)
    self.assert_('[xx]' in text)
    self.assert_('yy=zz' in text)

    # save again, this time got config.ini and a backup file
    self.cfg.set('xx.yy','11')
    self.cfg.save()
    self.assert_(os.path.exists(outfile))
    self.assert_(os.path.exists(outfile+'.~'))
#    outfile.remove()


 def test_str(self):
    s = str(self.cfg)


 def testSafeConfig(self):
    # make sure we are using safe test config

    keys = [n for n,v in testcfg.cparser.items('path')]
    # take these items outside of test
    keys.remove('docbase')
    keys.remove('testdoc')
    # check that the above code do what we want
    self.assert_('data' in keys)
    self.assert_('logs' in keys)
    self.assert_('weblibsnapshot' in keys)
    self.assert_('archiveindex' in keys)

    for name in keys:
        self.assert_('test' in testcfg.getpath(name))

    # we get test path even if we import from config
    from minds.config import cfg as config_cfg
    for name in keys:
        self.assert_('test' in config_cfg.getpath(name))



if __name__ == '__main__':
    unittest.main()