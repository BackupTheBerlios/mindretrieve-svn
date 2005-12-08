"""Look for a series of patterns in a file object.
This is used as a helper to unit testing.
"""

import re
from StringIO import StringIO
import unittest


def checkStrings(fp, strings, no_pattern=None):
    """
    Search for the series of strings in fp (one per line at most).
    In addition check for 'no_pattern' does not appear after the last pattern.
    Return none if all matched; or return the pattern not matched.
    """
    for s in strings:
        while True:
            line = fp.readline()
            if not line:
                return s            # fail to find s
            if s in line:
                break

    if no_pattern == None:
        return None                 # no_pattern not defined, we're done

    while True:
        line = fp.readline()
        if not line:
            return None             # end of file, we are still good
        if no_pattern in line:
            return no_pattern       # oops, we got the no_pattern



def checkPatterns(fp, patterns, no_pattern=None):
    """
    Similar to checkStrings() but use regular expressions.

    Note: the whole re pattern must appear within a line.
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
        self.assertEqual(p, None)

    def test01(self):
        p = checkPatterns(StringIO(''), ['X'])
        self.assertEqual(p, 'X')

    def test10(self):
        p = checkPatterns(StringIO('xyz'), [])
        self.assertEqual(p, None)

    def testCheckedOK(self):
        p = checkPatterns(StringIO(SAMPLE_FILE),
            ['html', '.text.css.', '</html>'])      # <-- .text.css. is an re
        self.assertEqual(p, None)

    def testCheckedRe(self):
        p = checkPatterns(StringIO(SAMPLE_FILE),
            ['html', '<title>.*</title>', '</html>'])
        self.assertEqual(p, None)

    def testOrderWrong(self):
        p = checkPatterns(StringIO(SAMPLE_FILE),
            ['html', r'\</html\>', '.text.css.'])
        self.assertEqual(p, '.text.css.')

    def testNoPatternGood(self):
        p = checkPatterns(StringIO(SAMPLE_FILE),
            ['html', '.text.css.', '</html>'],
            '<')
        self.assertEqual(p, None)

    def testNoPatternBad(self):
        p = checkPatterns(StringIO(SAMPLE_FILE),
            ['html', '.text.css.', '</head>'],
            '<')
        self.assertEqual(p, '<')


class TestCheckStrings(unittest.TestCase):

    def test00(self):
        p = checkStrings(StringIO(''), [])
        self.assertEqual(p, None)

    def test01(self):
        p = checkStrings(StringIO(''), ['X'])
        self.assertEqual(p, 'X')

    def test10(self):
        p = checkStrings(StringIO('xyz'), [])
        self.assertEqual(p, None)

    def testCheckedOK(self):
        p = checkStrings(StringIO(SAMPLE_FILE),
            ['html', 'text/css', '</html>'])
        self.assertEqual(p, None)

    def testOrderWrong(self):
        p = checkStrings(StringIO(SAMPLE_FILE),
            ['html', '</html>', 'text/css'])
        self.assertEqual(p, 'text/css')

    def testNoPatternGood(self):
        p = checkStrings(StringIO(SAMPLE_FILE),
            ['html', 'text/css', '</html>'],
            '<')
        self.assertEqual(p, None)

    def testNoPatternBad(self):
        p = checkStrings(StringIO(SAMPLE_FILE),
            ['html', 'text/css', '</head>'],
            '<')
        self.assertEqual(p, '<')


if __name__ == '__main__':
    unittest.main()