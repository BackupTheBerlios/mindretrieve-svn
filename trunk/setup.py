#!/usr/bin/python
from distutils.core import setup
import os
import py2exe
import glob
import stat
import sys
import tarfile

from minds import config


# If run without args, build executables, in quiet mode.
#if len(sys.argv) == 1:
#    sys.argv.append("py2exe")
#    sys.argv.append("-q")

APP_NAME = config.APPLICATION_NAME + config.cfg.get('version', 'number')
APP_NAME = APP_NAME.lower()

### todo: hack to include modules below:
from toollib import reindex


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
        self.version = config.cfg.get('version', 'number')
        self.company_name = config.APPLICATION_NAME
        self.copyright = "Copyright " + config.cfg.get('version', 'copyright')
        self.name = config.APPLICATION_NAME


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
            ('lib/testdocs',            glob.glob('lib/testdocs/*.*')),
            ('lib/testdocs/js',         glob.glob('lib/testdocs/js/*.*')),
            ('lib/testdocs/test_magic', glob.glob('lib/testdocs/test_magic/*.*')),
        ],
        )
