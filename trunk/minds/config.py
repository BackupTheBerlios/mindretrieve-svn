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

# 2005-09-03 Config Design (Why do we have this module instead of using ConfigParser directly?)
#
# - config (along with logging) is the most fundamental services. Allow customerization.
# - ConfigParser helps parsing and saving
# - 2 level address cumbersome. API to accept single address section.name.
# - bind together 2 config files and present as a single configuration.
# - parse boolean and integer fields with default fallback.


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
number=0.4.3
created=2005-02-21
copyright=2005
"""

APPLICATION_NAME = 'MindRetrieve'



### logging ############################################################

bootstrapHdlr = None

def setupLogging():
    """ 
    Setup a bootstrap logging to console. 
    Main program would use config to log to file later.
    """
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
        self.application_name = '%s %s' % (APPLICATION_NAME, self.get('version.number', '?'))
        self.pathname = ''


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
        self._setupPath(self.getPath('weblib'))


    def _setupPath(self, path):
        """ create directory if not already exists """
        if os.path.isdir(path): return
        try:
            os.makedirs(path)
        except OSError, e:
            # path exist but is not a directory?
            raise OSError, 'Unable to create directory specified in %s\n%s' % (self.pathname, e)


    def parseKey(self, key):
        parts = key.split('.',1)
        if len(parts) < 2:
            raise KeyError('Invalid configuration key: %s' % key)
        return parts
        
            
    def get(self, key, default=None):
        section, name = self.parseKey(key)
        try:
            return self.cparser.get(section, name)
        except Exception, e:
            if default != None: return default
            raise


    def getint(self, key, default=None):
        section, name = self.parseKey(key)
        try:
            return self.cparser.getint(section, name)
        except Exception, e:
            if default != None: return default
            raise


    def getboolean(self, key, default=None):
        section, name = self.parseKey(key)
        try:
            return self.cparser.getboolean(section, name)
        except Exception, e:
            if default != None: return default
            raise


    def getPath(self, name, default='.'):
        """ helper to get config from path section """
        return self.get('path.%s' % name, default)


    def set(self, key, value):
        section, option = self.parseKey(key)
        self.cparser.set(section, option, value)


    def __str__(self):
        buf = StringIO.StringIO()
        buf.write('Config pathname: %s\n' % self.pathname)
        buf.write('Config object: %s\n' % str(self.cparser))
        for s in self.cparser.sections():
            buf.write('\n[%s]\n' % s)
            for name, value in self.cparser.items(s):
                buf.write('%s=%s\n' % (name,value))
        return buf.getvalue()        


cfg = Config()


if __name__ == '__main__':
    unittest.main()