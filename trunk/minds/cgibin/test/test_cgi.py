import datetime
import sys
import unittest

from minds import app_httpserver
from minds import messagelog
from minds.util import fileutil
from minds.util import patterns_tester


class TestCGI(unittest.TestCase):

  def checkPathForPattern(self, path, patterns, nopattern=None):

    # note: look for </html> can ensure cgi did not abort in error
    buf = fileutil.aStringIO()
    app_httpserver.handlePath(path, buf)
    buf.seek(0)
    p = patterns_tester.checkPatterns(buf.read(), patterns, nopattern)
    # BUG: p can also be nopattern. In this case the msg should be 'pattern found!'
    self.assert_(not p,
        'Test failed path:%s\n  pattern not found: %s%s' % (path, p, patterns_tester.showFile(buf, 'out'))
    )

  def test_root(self):
    self.checkPathForPattern("/", ['<h1>MindRetrieve</h1>', '</html>'])

  def test_home(self):
    self.checkPathForPattern("/home", ['<h1>MindRetrieve</h1>', '</html>'])

  def test_library(self):
    self.checkPathForPattern("/library", ['<h1>MindRetrieve</h1>', '</html>'])

  def test_config(self):
    self.checkPathForPattern("/config", ['<h1>MindRetrieve</h1>', '</html>'])

  def test_help(self):
    self.checkPathForPattern("/help", ['<h1>MindRetrieve</h1>', '</html>'])

  def test_updateParent_input_escape(self):
    self.checkPathForPattern("/updateParent?url='\"</bad_tag>", ['<html>'], '</bad_tag>')



if __name__ == '__main__':
    unittest.main()