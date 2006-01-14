"""
Look for a series of patterns in a file object.
This is used as a helper to unit testing.
"""

import re
from StringIO import StringIO
import sys
import unittest

# this is a debugging aid. Can we make it easier to activate?
def _debug_mismatch(data, i, pattern):
    left = max(0,i-10)
    print >>sys.stderr, data[left:i] + '<$>' + data[i:i+20]
    print >>sys.stderr, 'Pattern not matched: ', pattern
    assert pattern


def checkStrings(data, patterns, no_pattern=None):
    """
    Search for the series of strings in data.
    In addition check for 'no_pattern' does not appear after the last pattern.
    Return none if all matched; or return the pattern not matched.
    """
    i = 0
    for p in patterns:
        j = data.find(p,i)
        if j < 0:
            return p
        i = j+len(p)

    if no_pattern and (data.find(no_pattern, i) >= 0):
        return no_pattern

    return None


def checkPatterns(data, patterns, no_pattern=None):
    """
    Similar to checkStrings() but use regular expressions.

    Note: the whole re pattern must appear within a line.
    """
    i = 0
    for p in patterns:
        m = re.compile(p,re.I).search(data, i)
        if not m:
            #_debug_mismatch(data,i,p)
            return p
        i = m.end()

    if no_pattern and re.compile(no_pattern,re.I).search(data, i):
        #_debug_mismatch(data,i,no_pattern)
        return no_pattern

    return None


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

class TestPatternTester(unittest.TestCase):

    def test00(self):
        p = checkPatterns('', [])
        self.assertEqual(p, None)

    def test01(self):
        p = checkPatterns('', ['X'])
        self.assertEqual(p, 'X')

    def test10(self):
        p = checkPatterns('xyz', [])
        self.assertEqual(p, None)

    def testCheckedOK(self):
        p = checkPatterns(SAMPLE_FILE,
            ['html', '.text.css.', '</html>'])      # <-- .text.css. is an re
        self.assertEqual(p, None)

    def testCheckedRe(self):
        p = checkPatterns(SAMPLE_FILE,
            ['html', '<title>.*</title>', '</html>'])
        self.assertEqual(p, None)

    def testOrderWrong(self):
        p = checkPatterns(SAMPLE_FILE,
            ['html', r'\</html\>', '.text.css.'])
        self.assertEqual(p, '.text.css.')

    def testNoPatternGood(self):
        p = checkPatterns(SAMPLE_FILE,
            ['html', '.text.css.', '</html>'],
            '<')
        self.assertEqual(p, None)

    def testNoPatternBad(self):
        p = checkPatterns(SAMPLE_FILE,
            ['html', '.text.css.', '</head>'],
            '<')
        self.assertEqual(p, '<')


class TestCheckStrings(unittest.TestCase):

    def test00(self):
        p = checkStrings('', [])
        self.assertEqual(p, None)

    def test01(self):
        p = checkStrings('', ['X'])
        self.assertEqual(p, 'X')

    def test10(self):
        p = checkStrings('xyz', [])
        self.assertEqual(p, None)

    def testCheckedOK(self):
        p = checkStrings(SAMPLE_FILE,
            ['html', 'text/css', '</html>'])
        self.assertEqual(p, None)

    def testOrderWrong(self):
        p = checkStrings(SAMPLE_FILE,
            ['html', '</html>', 'text/css'])
        self.assertEqual(p, 'text/css')

    def testNoPatternGood(self):
        p = checkStrings(SAMPLE_FILE,
            ['html', 'text/css', '</html>'],
            '<')
        self.assertEqual(p, None)

    def testNoPatternBad(self):
        p = checkStrings(SAMPLE_FILE,
            ['html', 'text/css', '</head>'],
            '<')
        self.assertEqual(p, '<')


if __name__ == '__main__':
    unittest.main()