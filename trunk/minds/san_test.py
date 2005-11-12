'''
Usage: san-test.py [options] basedir

Sanity test for Python project. Recursively load all '*.py' modules
under basedir. Search and run unit test cases. Report all modules that
cannot be imported (e.g. due to syntax error) and unit test cases
failed.


Options
 -n         no recursion
 -m module  test module specified
 --prefix   subclasses of unittest.TestCase with the prefix would be
            included in unit testing. Default is 'Test'.
'''
# todo: need to handle basedir = . e.g. import without package

import datetime
import fnmatch
import getopt
import logging
import StringIO
import sys, os, os.path
import traceback
import types
import unittest

from minds.safe_config import cfg
from toollib import HTMLTestRunner


def listModules(basedir, recurse=True):
    """ Recursively list all Python source file under basedir.
    """
    module_list = []
    for (dirpath, dirnames, filenames) in os.walk(basedir):
        if not recurse:
            del dirnames[:]
        filenames = fnmatch.filter(filenames,'*.py')
        if (dirpath != basedir) and ('__init__.py' not in filenames):
            continue
        package = dirpath.replace('\\','.').replace('/','.')
        for name in filenames:
            name = name[:-3]
            module_list.append((package,name))

    return module_list



def generate_allmodules(basedir, recurse):
    """ Generate allmodules.py and reload it """

    module_list = listModules(basedir, recurse)

    if not os.path.isdir(basedir):
        # assume this is frozen environment (e.g. Windows installer)
        # no need to regenerate and reload allmodules.py
        return

    fp = file('minds/allmodules.py','wb')
    fp.write('modules = ')
    s = repr(module_list)
    s = s.replace('),','),\n')
    fp.write(s)
    fp.close()


def loadModules(prefix):
    """ Return modules, errorlist, num_testmodules, suite. """

    try:
        from minds import allmodules
    except ImportError:
        traceback.print_exc()

    try:
        reload(allmodules)
    except ImportError:
        pass    # bug [856103] (https://sourceforge.net/tracker/?func=detail&atid=105470&aid=856103&group_id=5470)

    modules = []
    errorlist = []
    suite = unittest.TestSuite()
    num_testmodules = 0

    for (package, name) in allmodules.modules:
        package_name = '%s.%s' % (package, name)
        try:
            mod = __import__(package_name, globals(), locals(), [name])
        except Exception, e:
            buf = StringIO.StringIO()
            traceback.print_exc(file=buf)
            errorlist.append(buf.getvalue())
            continue

        modules.append(mod)
        module_suite = loadTestCases(mod, prefix)
        if module_suite:
            num_testmodules += 1
            suite.addTest(module_suite)

    if errorlist:
        for e in errorlist:
            sys.stderr.write('\n')
            sys.stderr.write(e)
        sys.stderr.write('-'*72)
        sys.stderr.write('\n')

    return modules, errorlist, num_testmodules, suite



def loadTestCases(module, prefix):
    """Return a suite of all tests cases contained in the given module"""

    # adapted from unittest.loadTestsFromModule, filter name with prefix
    tests = []
    for name in dir(module):
        if not name.startswith(prefix):
            continue
        obj = getattr(module, name)
        if (isinstance(obj, (type, types.ClassType)) and
            issubclass(obj, unittest.TestCase)):
            tests.append(name)

    if tests:
        return unittest.defaultTestLoader.loadTestsFromNames(tests, module)
    else:
        return None



def sanity_test(basedir, recurse, prefix):
    # remove any bootstrap log handler installed
    rootlog = logging.getLogger()
    map(rootlog.removeHandler, rootlog.handlers)

    # reinitialize logging with stdout_redirector
    logging.basicConfig(stream=HTMLTestRunner.stdout_redirector, level=logging.DEBUG)
    print >>sys.stderr, 'Date:', datetime.datetime.now()
    print >>sys.stderr, 'Basedir:', basedir

    generate_allmodules(basedir, recurse)
    modules, errorlist, num_testmodules, suite = loadModules(prefix)
#    unittest.TextTestRunner(verbosity=2).run(suite)
    HTMLTestRunner.HTMLTestRunner(verbosity=2).run(suite)


def _import(name):
    mod = __import__(name, globals(), locals())
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


# todo: largely cut & paste from sanity_test(). Consolidate?
def test_module(modname, prefix):
    # remove any bootstrap log handler installed
    rootlog = logging.getLogger()
    map(rootlog.removeHandler, rootlog.handlers)

    # reinitialize logging with stdout_redirector
    logging.basicConfig(stream=HTMLTestRunner.stdout_redirector, level=logging.DEBUG)
    print >>sys.stderr, 'Date:', datetime.datetime.now()

    suite = loadTestCases(_import(modname), prefix)

    HTMLTestRunner.HTMLTestRunner(verbosity=2).run(suite)



def main(argv):
    try:
        optlist, args = getopt.getopt(argv[1:], 'nm:', ['prefix='])
    except:
        print __doc__
        sys.exit(-1)

##    print >>sys.stderr, argv
##    print >>sys.stderr, optlist
  #  sys.exit(-1)
    basedir = 'minds'
    recurse = True
    modname = ''
    prefix = 'Test'
    for key, value in optlist:
        if key == '-n':
            recurse = False
        elif key == '-m':
            modname = value
        elif key =='--prefix':
            prefix = value

    if len(args) > 0: basedir = args[0]

    if not modname:
        sanity_test(basedir, recurse, prefix)
    else:
        test_module(modname, prefix)


if __name__ == '__main__':
    main(sys.argv)