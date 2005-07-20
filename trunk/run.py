#!/usr/bin/python
"""Usage: run.py option [module [arguments]]

options:

    --start     launch MindRetrieve
    --stop      stop MindRetrieve
    --san_test  launch sanity test
    --test      run unittest for module
    --run       invoke module
    --help      show this help
"""

import urllib
import sys, unittest


def testmain(argv):
    modname = argv[2]
    del argv[1:3]
    unittest.main(module=modname,argv=argv)



def run(argv):

    modname = argv[2]
    dot = modname.rfind('.')
    package_name = modname[0:dot]
    name = modname[dot+1:]
    mod = __import__(modname, globals(), locals(), [name])

    del sys.argv[1:3]
    print sys.argv
    mod.main(sys.argv)



def main(argv):
    if len(argv) <= 1:
        print __doc__
        sys.exit(-1)
        
    option = argv[1]

    if 'lib' not in sys.path:
        sys.path.append('lib')

    if option == '--start':
        from minds import proxy
        proxy.main()

    elif option == '--inproc_stop':
        from minds.config import cfg
        port = cfg.getint('http','admin_port',0)
        url = 'http://localhost:%d/config?action=shutdown' % port
        print url
        fp = urllib.urlopen(url)
        print fp.read()
        fp.close()

    elif option == '--stop':
        from minds.config import cfg
        port = cfg.getint('http','admin_port',0)
        url = 'http://localhost:%d/config?action=shutdown' % port
        print url
        fp = urllib.urlopen(url)
        print fp.read()
        fp.close()

    elif option == '--san_test':
        from minds import san_test
        del sys.argv[1:2]
        san_test.main(argv)

    elif option == '--test':
        testmain(argv)

    elif option == '--run':
        run(argv)

    elif option == '--help':
        print __doc__
        print sys.getdefaultencoding()



if __name__ == '__main__':
    main(sys.argv)