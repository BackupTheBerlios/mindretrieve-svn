"""
This module loads a configuration file and setup basic logging.

Instead of loading this module directly, import either one of the two
convenient module.

In test code, import safe_config as the first module like

    from minds.safe_config import cfg as test_Cfg

In application code, load the actual configuration file by importing
config as first first module like

    from minds.config import cfg
"""

import ConfigParser
import datetime
import logging, logging.handlers
import os
import os.path
import StringIO
import sys

from toollib.path import path

# 2005-09-03 Config Design (Why do we have this module instead of using ConfigParser directly?)
#
# - config (along with logging) is the most fundamental services. Allow customerization.
# - ConfigParser helps parsing and saving.
# - 2 level address cumbersome. API to accept single address as 'section.name'.
# - bind together 2 config files and present as a single configuration. (is 2 config files a good idea?)
# - parse boolean and integer fields with default fallback.

# The order configuration

# 1. user setting
# 2. factory shipped config value
# 3. SYSTEM_DEFAULT_CONFIG
# 4. logic default

# A note about 3 and 4. "4. logic default" is the default value a module
# pass when calling cfg.getXXX(). A module is encouraged to supply a
# sensible default to protect the system in case of failure to find the
# configuration file. The choice of default is delegated to the module
# that has best knowledge. Ideally the value should be the same as 2.
# "3. SYSTEM_DEFAULT_CONFIG" is a backup to 4. when it make more sense
# to have centralized definition.

# Issue: since 3 is recommended to be the same as 2. This introduced
# some redundancy the is best minimized.



# ------------------------------------------------------------------------

CONFIG_FILE = 'config.ini'

# burnin information
APPLICATION_NAME = 'MindRetrieve'
VERSION = '0.8.2'
CREATED = '2006-03-27'


# TODO: we don't really need this? move to test?

# Minimal default system config. To over overridden by CONFIG_FILE.
# Note: the default path section points to testdata and testlogs for unit testing.
SYSTEM_DEFAULT_CONFIG="""[path]
data=testdata
archive=testdata/archive
archiveindex=testdata/archive/index
weblib=testdata/weblib
weblibsnapshot=testdata/weblib.snapshot
weblibindex=testdata/weblib.index
docBase=lib/htdocs
testDoc=lib/testdocs
logs=testlogs
"""


# ------------------------------------------------------------------------

def setupLogging():
    """
    Setup a bootstrap logging to console.
    Main program would use config to log to file later.
    """
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

setupLogging()
log = logging.getLogger('cfg')


# ------------------------------------------------------------------------

# the singleton instance
cfg = None

class Config(object):
    """ Provides a default config; setup paths """

    def __init__(self):
        """ initialize with default config file """
        self.cparser = ConfigParser.RawConfigParser()
        self.cparser.readfp( StringIO.StringIO(SYSTEM_DEFAULT_CONFIG), 'System Default')
        self.application_name = '%s %s' % (APPLICATION_NAME, VERSION)
        self.config_path = ''


    def load(self, pathname=''):
        """ Load a configuration file. Intended to be called only once. """
        if pathname:
            self.config_path = path(pathname)
            # ConfigParser.read() do nothing if name does not exist. Check first.
            if not self.config_path.exists():
                log.error('Config file does not exist: %s', self.config_path)
                return
            log.info('Loading config file: %s', self.config_path)
            self.cparser.read(self.config_path)

        # always override with burnin VERSION
        self.set('_system.version', VERSION)
        self.set('_system.created', CREATED)


    def load_test_config(self):
        """ reset paths to default test directory """
        self.load(CONFIG_FILE)
        # reapply SYSTEM_DEFAULT_CONFIG to get the test paths
        self.cparser.readfp( StringIO.StringIO(SYSTEM_DEFAULT_CONFIG), 'System Default')
        log.info('Load test config. Data path: %s', self.getpath('data'))


    def save(self):
        today = str(datetime.date.today())
        log.info('Saving config file: %s %s' % (self.config_path, today))
        self.set('_system.updated', today)
        wpath = self.config_path + '.tmp'
        bpath = self.config_path + '.~'
        fp = file(wpath,'wb')
        try:
            self._serialize(fp)
        finally:
            fp.close()
        from minds.util import fileutil
        fileutil.shift_files([wpath, self.config_path, bpath])


    def setupPaths(self):
        """ Create directories specified in [path] """
        self._setupPath(self.getpath('logs'))
        self._setupPath(self.getpath('archive'))
        self._setupPath(self.getpath('weblibsnapshot'))
        self._setupPath(self.getpath('weblib'))


    def _setupPath(self, pathname):
        """ create directory if not already exists """
        if pathname.isdir(): return
        try:
            pathname.makedirs()
        except OSError, e:
            # path exist but is not a directory?
            raise OSError, 'Unable to create directory specified in %s\n%s' % (pathname, e)


    def _parseKey(self, key):
        parts = key.split('.',1)
        if (len(parts) < 2) or (not parts[0]) or (not parts[1]):
            raise KeyError('Invalid configuration key: %s' % key)
        return parts


    def get(self, key, default=None):
        section, name = self._parseKey(key)
        try:
            return self.cparser.get(section, name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError), e:
            if default != None: return default
            raise KeyError(str(e))


    def getint(self, key, default=None):
        section, name = self._parseKey(key)
        try:
            return self.cparser.getint(section, name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError), e:
            if default != None: return default
            raise KeyError(str(e))
        except ValueError, e:
            if default != None: return default
            raise


    def getboolean(self, key, default=None):
        section, name = self._parseKey(key)
        try:
            return self.cparser.getboolean(section, name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError), e:
            if default != None: return default
            raise KeyError(str(e))
        except ValueError, e:
            if default != None: return default
            raise


    def getpath(self, name, default='.'):
        """ helper to get config from path section """
        pathname = self.get('path.%s' % name, default)
        return path(pathname)


    def set(self, key, value):
        section, option = self._parseKey(key)
        if not self.cparser.has_section(section):
            self.cparser.add_section(section)
        self.cparser.set(section, option, value)


    def _serialize(self, fp):
        for s in sorted(self.cparser.sections()):
            if s:
                fp.write('[%s]\n' % s)
            for name, value in sorted(self.cparser.items(s)):
                value = str(value).replace('\n', '\n\t')
                fp.write('%s=%s\n' % (name,value))
            fp.write('\n')


    def __str__(self):
        buf = StringIO.StringIO()
        self._serialize(buf)
        return 'Config file: %s\n%s' % (self.config_path, buf.getvalue())


    def readObject(self, prefix, required_attrs, optional_attrs):
        """
        Read object in the format of:

        [prefix.ddd]
        name1=value1
        name2=value2

        Build object with the attribute names referencing values.
        Return list of objects.
        """
        prefix += '.'
        result = []
        for section in self.cparser.sections():
            if not section.startswith(prefix):
                continue
            try:
                id = int(section[len(prefix):])
            except:
                continue

            # build attributes dictionary
            items = self.cparser.items(section)
            attrs = dict([(name, value) for name, value in items
                        if name in required_attrs or name in optional_attrs])

            # has all the required fields?
            data = None
            for r in required_attrs:
                if r not in attrs:
                    log.warn('Section "%s" kissing required attribute "%s"', section, r)
                    break
            else:
                data = DataObject()
            if not data:
                continue

            data.__dict__.update(attrs)
            result.append(data)

        return result


class DataObject:
    def __init__(self):
        pass
    def __repr__(self):
        return str(self.__dict__)



# ----------------------------------------------------------------------
# cmdline testing

def main(argv):
#    from minds.safe_config import cfg
    from minds.config import cfg
    print cfg
    while True:
        print '\nEnter key to query. Enter key=value to set. "show" to show all values. "save" to save config.'
        line = raw_input('Config key: ')
        if not line:
            break

        if line == 'show':
            print cfg
            continue
        elif line =='save':
            cfg.save()
            continue

        # set key=value?
        if '=' in line:
            key, value = line.split('=',1)
            cfg.set(key, value)
        else:
            key = line
        # query
        try:
            value = cfg.get(key,'n/a')
            print '%s=%s' % (key,value)
        except Exception, e:
            print e


def testReadObject():
    from minds.config import cfg
    o = cfg.readObject('search_engine',['id','url','label'],['shortcut','history','method','encoding'])
    from pprint import pprint
    pprint(o)


if __name__ =='__main__':
    #testReadObject()
    main(sys.argv)
