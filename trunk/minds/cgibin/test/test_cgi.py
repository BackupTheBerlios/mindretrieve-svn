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
    self.checkPathForPattern("/", ['302 Found'])

  def test_help(self):
    self.checkPathForPattern("/help", ['<html>', 'Getting Started','</html>'])

  def test_help_gettingstarted(self):
    self.checkPathForPattern("/help/GettingStarted", ['<html>', 'Getting Started','</html>'])

  def test_help_proxyinstruction(self):
    self.checkPathForPattern("/help/ProxyInstruction", ['<html>', 'Proxy Instruction','</html>'])

  def test_control(self):
    self.checkPathForPattern("/___", ['Date'])

  def test_updateParent_input_escape(self):
    self.checkPathForPattern("/updateParent?url='\"</bad_tag>", ['<html>'], '</bad_tag>')

  def test_control(self):
    self.checkPathForPattern("/___", ['Date'])


if __name__ == '__main__':
    unittest.main()