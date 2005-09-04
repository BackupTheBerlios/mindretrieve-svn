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

from toollib.path import path

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
[version]
number=0.4.3
created=2005-02-21
copyright=2005

[path]
data=testdata
archive=testdata/archive
archiveindex=testdata/archive/index
weblib=testdata/weblib
weblibindex=testdata/weblib/index
docBase=lib/htdocs
testDoc=lib/testdocs
logs=logs

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
"""

APPLICATION_NAME = 'MindRetrieve'

# essential system configuration; usually ship with product
CONFIG_FILE = 'config.ini'

# user preference
PREFERENCE_FILE = 'preference.ini'


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
        self.pparser = ConfigParser.ConfigParser()
        self.application_name = '%s %s' % (APPLICATION_NAME, self.get('version.number', '?'))
        self.config_pathname = ''
        self.pref_pathname = ''


    def load(self, pathname):
        """ Load a configuration file. Intended to be called only once. """
        logging.getLogger().info('Loading config file: %s', pathname)
        # ConfigParser.read() do nothing if name does not exist. Check first.
        if not os.path.exists(pathname):
            logging.getLogger().error('Config file does not exist: %s', pathname)
            return
            
        self.config_pathname = pathname
        self.cparser.read(pathname)
        
        self.pref_pathname = path(self.getPath('data')) / PREFERENCE_FILE
        logging.getLogger().info('Loading preference file: %s', self.pref_pathname)
        
        # merge with pref
        self.cparser.read(self.pref_pathname)
        
        # pparser is mainly used for save
        self.pparser.read(self.pref_pathname)


    def setupPaths(self):
        """ Create directories specified in [path] """
        self._setupPath(self.getPath('logs'))
        self._setupPath(self.getPath('archive'))
        self._setupPath(self.getPath('weblib'))


    def _setupPath(self, pathname):
        """ create directory if not already exists """
        if os.path.isdir(pathname): return
        try:
            os.makedirs(pathname)
        except OSError, e:
            # path exist but is not a directory?
            raise OSError, 'Unable to create directory specified in %s\n%s' % (pathname, e)


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


    def update_pref(items):
        """
        @params items - list of key, value tuples 
        """
        for k,v in items:
            section, name = self.parseKey(key)
            self.cparser.set(section, name, value)
            self.pparser.set(section, name, value)
            
        logging.getLogger().error('Updating preference: %s', self.pref_pathname)
        fp = file(self.pref_pathname,'wb')
        try:
            self.pparser.write(fp)
        finally:
            fp.close()    
        
        
    def __str__(self):
        buf = StringIO.StringIO()
        buf.write('Config file: %s\n' % self.config_pathname)
        buf.write('Preference file: %s\n' % self.pref_pathname)
        for s in self.cparser.sections():
            buf.write('\n[%s]\n' % s)
            for name, value in self.cparser.items(s):
                buf.write('%s=%s\n' % (name,value))
        return buf.getvalue()        

cfg = Config()

# ----------------------------------------------------------------------
# cmdline testing

def main(argv):
    cfg.load(CONFIG_FILE)
    print cfg
    while True:
        line = raw_input('Config key: ')
        if not line:
            break
        try:    
            value = cfg.get(line,'n/a')
            print line,'=',value
        except Exception, e:
            print e    
        

if __name__ =='__main__':
    main(sys.argv)
