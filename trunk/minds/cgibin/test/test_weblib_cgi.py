import datetime
import os, sys
import shutil
import unittest

from minds import app_httpserver
from minds.test.config_help import cfg
from minds.util import fileutil
from minds.util import patterns_tester
from minds import weblib
from minds.weblib import store
from toollib.path import path

testdir = path(cfg.getPath('testDoc'))

class TestWeblibCGI(unittest.TestCase):

  def setUp(self):
    global TEST_WORK_FILENAME  
    ## todo: move to some util?
    from minds.weblib import store
    # rewire store to use the working copy of test weblib.dat
    TEST_PATHNAME = testdir / 'test_weblib/weblib.dat'
    # TODO: now that we have testdata directory, don't need to call it weblib.work.dat anymore.
    # TODO: clean up
    TEST_WORK_FILENAME = 'weblib.work.dat'
    weblibdir = path(cfg.getPath('weblib'))
    shutil.copy(TEST_PATHNAME, weblibdir / TEST_WORK_FILENAME)
    print >>sys.stderr, TEST_PATHNAME, weblibdir / TEST_WORK_FILENAME, '##',path(cfg.getPath('weblib'))
    store.useMainBm(TEST_WORK_FILENAME)

#  def tearDown(self):
#    global i  
#    i+=1  
#    shutil.copy(TEST_WORK_FILENAME, TEST_WORK_FILENAME+str(i))
#    print >>sys.stderr,   TEST_WORK_FILENAME+str(i)

  def checkPathForPattern(self, path, patterns, no_pattern=None):
    buf = fileutil.aStringIO()
    app_httpserver.handlePath(path, buf)
    buf.seek(0)
    p = patterns_tester.checkPatterns(buf, patterns, no_pattern)
    msg = (p == no_pattern) and 'unexpected pattern found' or 'pattern missing'
    self.assert_(not p,
        'failed:%s\n  %s: %s%s' % (
            path, 
            msg,
            p, 
            patterns_tester.showFile(buf, 'out', 1024),
    ))

  def test_weblib(self):
    self.checkPathForPattern("/weblib", [
        '<html>', 
        'www.mindretrieve.net',     # this entry appears on main page
        '</html>',
    ])

    # controlled test for below
    # ja.wikipedia.org will not be listed unless there is a right query
    self.checkPathForPattern("/weblib", [
        '<html>',
        ], 
        'ja.wikipedia.org'
    )

    self.checkPathForPattern("/weblib?tag=English", [
        '<html>',
        ], 
        'ja.wikipedia.org'
    )


  def test_weblib_tag(self):
    # this is the URL encoded for the Japanese tag
    self.checkPathForPattern("/weblib?tag=%E6%97%A5%E6%9C%AC%E8%AA%9E", [
        '<html>', 
        'ja.wikipedia.org', 
        '</html>',
    ])


  def test_weblib_query(self):
    self.checkPathForPattern("/weblib?query=%20-%20Wikipedia", [
        '<html>', 
        'ja.wikipedia.org', 
        '</html>',
    ])


  def test_weblib_go(self):
    self.checkPathForPattern("/weblib/4/go;url", [
        'HTTP/1.0 302 Found',
        'ja.wikipedia.org', 
        ],
        '</html>'
    )


  def test_weblib_form_new(self):
    self.checkPathForPattern("/weblib/_", [
        '<html>', 
        'Add Entry',
        '</html>',
    ])
    self.checkPathForPattern("/weblib/_/form", [
        '<html>', 
        'Add Entry',
        '</html>',
    ])

  def test_weblib_put_form_new(self):
    wlib = store.getMainBm()
    self.assertEqual(len(wlib.webpages),5)

    # PUT new form
    self.checkPathForPattern("/weblib/_?method=put&filled=1&u=http%3A%2F%2Fwww.mindretrieve.net%2F&t=Test%20Title", [
        'HTTP/1.0 302 Found', 
        'location: /weblib',
    ])
    
    # one item has added
    self.assertEqual(len(wlib.webpages),6)


  def test_weblib_form(self):
    self.checkPathForPattern("/weblib/4", [
        '<html>', 
        'Edit Entry',
        'ja.wikipedia.org', 
        '</html>',
    ])
    self.checkPathForPattern("/weblib/4/form", [
        '<html>', 
        'Edit Entry',
        'ja.wikipedia.org', 
        '</html>',
    ])


  def test_weblib_put_form(self):
    wlib = store.getMainBm()
    self.assertEqual(len(wlib.webpages),5)
    item = wlib.webpages.getById(1)
    self.assertEqual(item.name, 'MindRetrieve - Search Your Personal Web')

    # PUT form    
    self.checkPathForPattern("/weblib/1?method=put&filled=1&u=http%3A%2F%2Fwww.mindretrieve.net%2F&t=Test%20Title", [
        'HTTP/1.0 302 Found', 
        'location: /weblib',
    ])
    
    # one item has changed
    self.assertEqual(len(wlib.webpages),5)
    item = wlib.webpages.getById(1)
    self.assertEqual(item.name, 'Test Title')


if __name__ == '__main__':
    unittest.main()