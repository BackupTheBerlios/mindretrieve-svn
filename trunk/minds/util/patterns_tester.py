"""Look for a series of patterns in a file object.
This is used as a helper to unit testing.
"""

import re
from StringIO import StringIO
import unittest


def checkPatterns(fp, patterns, no_pattern=None):
    """ Search for the series of 'patterns' in fp (one per line at most).
        In addition check for 'no_pattern' does not appear after the last pattern.
        Return none if all matched; or return the pattern not matched.
    """
    for p in patterns:
        pre = re.compile(p, re.I)
        while True:
            line = fp.readline()
            if not line:
                return p            # fail to find pattern p
            if pre.search(line):
                break

    if no_pattern == None:
        return None                 # no_pattern not defined, we're done

    pre = re.compile(no_pattern, re.I)
    while True:
        line = fp.readline()
        if not line:
            return None             # end of file, we are still good
        if pre.search(line):
            return no_pattern       # oops, we got the no_pattern



def showFile(fp, label, maxchars=1024):
    """ show a buffered file (e.g. StringIO), truncate after max chars """

    fp.seek(0)
    data = fp.read(maxchars)
    if fp.read(1):
        extra = '...'
    else:
        extra = ''

    document = """
--%s%s
%s%s
--^end-----------------------------------------------------------------
""" % (label, '-' * (70-len(label)), data, extra)

    return document



# ----------------------------------------------------------------------
# Test the tester

SAMPLE_FILE = """
<html>
<head>
  <title>Home</title>
  <link rel="stylesheet" href="/main.css" type="text/css">
  <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">
</head>
</html>
"""

# todo: give a little explanation on each test
# todo: use assertEqual instead of assert_

class TestPatternTester(unittest.TestCase):

    def test00(self):
        p = checkPatterns(StringIO(''), [])
        self.assert_(not p, 'unexpected: %s' % p)

    def test01(self):
        p = checkPatterns(StringIO(''), ['X'])
        self.assertEqual(p, 'X')

    def test10(self):
        p = checkPatterns(StringIO('xyz'), [])
        self.assert_(not p, 'unexpected: %s' % p)

    def testCheckedOK(self):
        p = checkPatterns(
            StringIO(SAMPLE_FILE),
            ['html', '.text.css.', '</html>'])
        self.assert_(not p, 'unexpected: %s' % p)

    def testOrderWrong(self):
        p = checkPatterns(
            StringIO(SAMPLE_FILE),
            ['html', r'\</html\>', '.text.css.'])
        self.assertEqual(p, '.text.css.')

    def testNoPatternGood(self):
        p = checkPatterns(
            StringIO(SAMPLE_FILE),
            ['html', '.text.css.', '</html>'],
            '<')
        self.assert_(not p, 'unexpected: %s' % p)

    def testNoPatternBad(self):
        p = checkPatterns(
            StringIO(SAMPLE_FILE),
            ['html', '.text.css.', '</head>'],
            '<')
        self.assertEqual(p, '<')


if __name__ == '__main__':
    unittest.main()