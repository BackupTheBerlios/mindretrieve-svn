"""
This module loads a configuration file and setup basic logging.
This is a light weight suitable for import from unit testing.

Import this module as the first application module.
"""

import ConfigParser
import logging, logging.handlers
import os
import os.path
import StringIO
import sys

# This is intended to synchronize with the CONFIG_FILE edited by user.
# This can be a hardcoded fallback in case user has mess up the file.

# Note: Keep the setting below to put test log is its own directory
#   logs=testlogs, archive=testdata/archive, etc

SYSTEM_DEFAULT_CONFIG="""
[path]
archive=testdata/archive
archiveindex=testdata/archive/index
docBase=lib/htdocs
testDoc=lib/testdocs
logs=testlogs

[http]
proxy_port=8051
proxy_threads=10
admin_port=8050
http_proxy=

[messagelog]
max_messagelog=2048
maxuri=1024
mlog=

[indexing]
interval=3
numDoc=50
max_interval=360
archive_interval=1

[filter]
domain.0=.googlesyndication.com
domain.1=
domain.2=
domain.3=
domain.4=

[version]
number=0.4.0
created=2005-01-22
copyright=2005
"""

APPLICATION_NAME = 'MindRetrieve'



### logging ############################################################

bootstrapHdlr = None

def setupLogging():
    """ Setup a bootstrap logging to console """

    # why do we need to setup a bootstrap logger?
    # Can't logging send to console by default?
    global bootstrapHdlr
    bootstrapHdlr = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s %(name)-10s - %(message)s')
    bootstrapHdlr.setFormatter(formatter)
    rootlog = logging.getLogger()
    rootlog.addHandler(bootstrapHdlr)
    rootlog.setLevel(logging.DEBUG)

setupLogging()


### config file ########################################################

class Config(object):
    """ Provides a default config; setup paths """

    def __init__(self):
        """ initialize with default config file """
        self.cparser = ConfigParser.ConfigParser()
        self.cparser.readfp( StringIO.StringIO(SYSTEM_DEFAULT_CONFIG), 'System Default')
        self.application_name = '%s %s' % (APPLICATION_NAME, self.get('version', 'number', '?'))


    def load(self, pathname):
        """ Load a configuration file. Intended to be called only once. """
        logging.getLogger().info('Loading config file: %s', pathname)
        # ConfigParser.read() do nothing if name does not exist. Check first.
        if not os.path.exists(pathname):
            logging.getLogger().error('Config file does not exist: %s', pathname)
        else:
            self.pathname = pathname
            self.cparser.read(pathname)


    def setupPaths(self):
        """ Create directories specified in [path] """
        self._setupPath(self.getPath('logs'))
        self._setupPath(self.getPath('archive'))


    def _setupPath(self, path):
        """ create directory if not already exists """
        if os.path.isdir(path): return
        try:
            # raise exception if path exist but is not a directory
            os.makedirs(path)
        except OSError, e:
            raise OSError, 'Unable to create directory specified in %s\n%s' % (self.pathname, e)


    def get(self, section, name, default=None):
        try:
            return self.cparser.get(section, name)
        except Exception, e:
            if default != None: return default
            raise e


    def getint(self, section, name, default=None):
        try:
            return self.cparser.getint(section, name)
        except Exception, e:
            if default != None: return default
            raise e


    def getboolean(self, section, name, default=None):
        try:
            return self.cparser.getboolean(section, name)
        except Exception, e:
            if default != None: return default
            raise e


    def getPath(self, name, default='.'):
        """ helper to get config from path section """
        return self.get('path', name, default)


    def set(self, section, option, value):
        self.cparser.set(section, option, value)


    def dump(self, out):
        out.write('Config object: %s\n' % str(self.cparser))
        for s in self.cparser.sections():
            out.write('Section: %s\n' % s)
            for name, value in self.cparser.items(s):
                out.write('  %s=%s\n' % (name,value))


cfg = Config()


### testing ############################################################

import unittest

TEST_FILENAME = 'config.ini'

class TestConfig(unittest.TestCase):

  def setUp(self):
    # save cfg which would get modified in testConfig
    global cfg
    self.cfg0 = cfg
    cfg = Config()

  def testConfig(self):
    print '\n@testConfig:', TEST_FILENAME
    cfg.load(TEST_FILENAME)
    cfg.setupPaths()
    cfg.dump(sys.stdout)
    self.assertEqual( cfg.get('version','created'), '2005-01-22')

  def testDefault(self):
    self.assertNotEqual( cfg.get('version','created','X'), 'X')         # not using default

    self.assertEqual( cfg.get('version','keyX', 'default'), 'default')
    self.assertEqual( cfg.get('version','keyX', ''       ), '')         # Test out default of ''

    self.assertEqual( cfg.getint    ('version','keyX', 1     ), 1)
    self.assertEqual( cfg.getint    ('version','keyX', 0     ), 0)      # Test out default of 0

    self.assertEqual( cfg.getboolean('version','keyX', True  ), True )
    self.assertEqual( cfg.getboolean('version','keyX', False ), False)  # Test out default of False

  def tearDown(self):
    global cfg
    cfg = self.cfg0

if __name__ == '__main__':
    unittest.main()