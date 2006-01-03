from distutils.core import setup
import os
import py2exe
import glob
import stat
import sys
import tarfile

from minds.config import cfg
from minds import base_config


APP_NAME = cfg.application_name
APP_NAME = APP_NAME.lower()

### todo: hack to include modules below:
from toollib import reindex


################################################################
# win32com.shell and py2exe hack
#   http://starship.python.net/crew/theller/moin.cgi/WinShell

# ModuleFinder can't handle runtime changes to __path__, but win32com uses them
try:
    import modulefinder
    import win32com
    for p in win32com.__path__[1:]:
        modulefinder.AddPackagePath("win32com", p)
    for extra in ["win32com.shell"]: #,"win32com.mapi"
        __import__(extra)
        m = sys.modules[extra]
        for p in m.__path__[1:]:
            modulefinder.AddPackagePath(extra, p)
except ImportError:
    # no build path setup, no worries.
    pass

################################################################

def addscript(tf, name, arcname):
    tinfo = tf.gettarinfo(name, arcname)
    tinfo.mode |= stat.S_IXUSR+stat.S_IXGRP
    fp = file(name,'rb')
    tf.addfile(tinfo, fp)
    fp.close()


def make_sdist(argv):

    files = [
      ('dist/config.ini',       'config.ini'            ),
      ('dist/license.txt',      'license.txt'           ),
      ('dist/docs',             'docs'                  ),
      ('dist/lib/htdocs',       'lib/htdocs'            ),
      ('dist/lib/testdocs',     'lib/testdocs'          ),
      ('sitecustomize.py',      'lib/sitecustomize.py'  ),
    ]

    files += [(f, 'lib/'+f) for f in glob.glob('minds/*.py')]
    files += [(f, 'lib/'+f) for f in glob.glob('minds/*/*.py')]
    files += [(f, 'lib/'+f) for f in glob.glob('minds/*/*/*.py')]
    files += [(f, 'lib/'+f) for f in glob.glob('toollib/*.py')]

    # make the distribution file
    tf = tarfile.open(APP_NAME+'.tar.gz','w:gz')
    for name, arcname in files:
        tf.add(name, APP_NAME + '/' + arcname)
    addscript(tf, 'run.py',   APP_NAME + '/' +'run.py')
    addscript(tf, 'setup.py', APP_NAME + '/' +'setup.py')

    tf.close()



################################################################

class Target:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        # for the versioninfo resources
        self.version = cfg.get('version.number')
        self.company_name = base_config.APPLICATION_NAME
        self.copyright = "Copyright " + cfg.get('version.copyright')
        self.name = base_config.APPLICATION_NAME


################################################################
# a NT service, modules is required
myservice = Target(
    # used for the versioninfo resource
    description = "MindRetrieve Windows NT service",
    # what to build.  For a service, the module name (not the
    # filename) must be specified!
    modules = ["MindRetrieve"]
    )


################################################################
# COM pulls in a lot of stuff which we don't want or need.

excludes = ["pywin", "pywin.debugger", "pywin.debugger.dbgcon",
            "pywin.dialogs", "pywin.dialogs.list"]

if 'sdist' in sys.argv:

    # In my opinion distutil's sdist command is quite broken.
    # Hack my own here. Should ran only immediately after "setup.py py2exe".
    make_sdist(sys.argv)

else:

    setup(
        options = {"py2exe": {
    #                          # create a compressed zip archive
    #                          "compressed": 1,
                              "optimize": 2,
                              "excludes": excludes,
                              "packages": [
                                  "encodings",
                                  "minds",
                                  "minds.cgibin",
                                  "minds.cgibin.test",
                                  "minds.test",
                                  "minds.util",
                                  ],
                              }},
        # The lib directory contains everything except the executables and the python dll.
        # Can include a subdirectory name.
        zipfile = "lib/shared.zip",

        console=['run.py'],
        service = [myservice],
        data_files=[
            ('.', [
                'config.ini',
                'docs/license.txt',
            ]),
            ('docs',                    ['docs/website/readme.html',]),
            ('docs',                    ['docs/build.txt',]),
            ('docs/img',                glob.glob('docs/website/img/firefox_proxy.gif')),
            ('docs/img',                glob.glob('docs/website/img/ie_proxy.gif')),
            ('docs/img',                glob.glob('docs/website/img/opera_proxy.gif')),
            ('.',                       ['lib/msvcr71.dll',]),
            ('lib/htdocs',              glob.glob('lib/htdocs/*.*')),
            ('lib/htdocs/img',          glob.glob('lib/htdocs/img/*.*')),
            ('lib/testdocs',            glob.glob('lib/testdocs/*.*')),
            ('lib/testdocs/js',         glob.glob('lib/testdocs/js/*.*')),
            ('lib/testdocs/test_magic', glob.glob('lib/testdocs/test_magic/*.*')),
        ],
        )
