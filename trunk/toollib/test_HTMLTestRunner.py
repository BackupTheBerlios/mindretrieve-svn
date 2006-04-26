# -*- coding: utf-8 -*-

import StringIO
import sys
import unittest

import HTMLTestRunner

# ----------------------------------------------------------------------

def safe_unicode(obj, *args):
    """ return the unicode representation of obj """
    try:
        return unicode(obj, *args)
    except UnicodeDecodeError:
        # obj is byte string
        ascii_text = str(obj).encode('string_escape')
        return unicode(ascii_text)

def safe_str(obj):
    """ return the byte string representation of obj """
    try:
        return str(obj)
    except UnicodeEncodeError:
        # obj is unicode
        return unicode(obj).encode('unicode_escape')

# ----------------------------------------------------------------------
# Sample tests to drive the HTMLTestRunner

class BaseTest(unittest.TestCase):
    def test_1(self):
        print self.MESSAGE
    def test_2(self):
        print >>sys.stderr, self.MESSAGE
    def test_3(self):
        self.fail(self.MESSAGE)
    def test_4(self):
        raise RuntimeError(self.MESSAGE)

class TestBasic(BaseTest):
    MESSAGE = 'basic test'

class TestHTML(BaseTest):
    MESSAGE = 'the message is <>&"\'\nline2'

class TestLatin1(BaseTest):
    MESSAGE = u'the message is áéíóú'.encode('latin-1')

class TestUnicode(BaseTest):
    MESSAGE = u'the message is \u8563'
    # 2006-04-25 Note: Exception would show up as
    # AssertionError: <unprintable instance object>
    #
    # This seems to be limitation of traceback.format_exception()
    # Same result in standard unittest.

# ------------------------------------------------------------------------
# This is the main test on HTMLTestRunner

class Test_HTMLTestRunner(unittest.TestCase):

    # Define the expected output sequence. This is imperfect but should
    # give a good sense of the well being of the test.
    EXPECTED = u"""
>__main__.TestBasic<
>test_1<
>pass<
basic test

>test_2<
>pass<
basic test

>test_3<
>fail<
AssertionError: basic test

>test_4<
>error<
RuntimeError: basic test


>__main__.TestHTML<
>test_1<
>pass<
'the message is &lt;&gt;&amp;&quot;&apos;\nline2

>test_2<
>pass<
'the message is &lt;&gt;&amp;&quot;&apos;\nline2

>test_3<
>fail<
AssertionError: the message is &lt;&gt;&amp;&quot;&apos;\nline2

>test_4<
>error<
RuntimeError: the message is &lt;&gt;&amp;&quot;&apos;\nline2


>__main__.TestLatin1<
>test_1<
>pass<
the message is áéíóú

>test_2<
>pass<
the message is áéíóú

>test_3<
>fail<
AssertionError: the message is áéíóú

>test_4<
>error<
RuntimeError: the message is áéíóú


>__main__.TestUnicode<
>test_1<
>pass<
the message is \u8563

>test_2<
>pass<
the message is \u8563

>test_3<
>fail<
AssertionError: &lt;unprintable instance object&gt;

>test_4<
>error<
RuntimeError: &lt;unprintable instance object&gt;

Total
>16<
>8<
>4<
>4<
</html>
"""

    def test1(self):
        # Run HTMLTestRunner. Verify the HTML report.

        # suite of TestCases
        self.suite = unittest.TestSuite()
        self.suite.addTests([
            unittest.defaultTestLoader.loadTestsFromTestCase(TestBasic),
            unittest.defaultTestLoader.loadTestsFromTestCase(TestHTML),
            unittest.defaultTestLoader.loadTestsFromTestCase(TestLatin1),
            unittest.defaultTestLoader.loadTestsFromTestCase(TestUnicode),
            ])

        # Invoke TestRunner
        buf = StringIO.StringIO()
        #runner = unittest.TextTestRunner(buf)       #DEBUG: this is the unittest baseline
        runner = HTMLTestRunner.HTMLTestRunner(buf)
        runner.run(self.suite)

        # check out the output
        byte_output = buf.getvalue()
        # for user to capture the output to see what goes wrong
        print byte_output
        # HTMLTestRunner pumps UTF-8 output
        output = byte_output.decode('utf-8')
        self._checkoutput(output)


    def _checkoutput(self,output):
        i = 0
        for lineno, p in enumerate(self.EXPECTED.splitlines()):
            if not p:
                continue
            j = output.find(p,i)
            if j < 0:
                self.fail(safe_str('Pattern not found lineno %s: "%s"' % (lineno+1,p)))
            i = j + len(p)




##############################################################################
# Executing this module from the command line
##############################################################################

import unittest
if __name__ == "__main__":
    if len(sys.argv) > 1:
        argv = sys.argv
    else:
        argv=['test_HTMLTestRunner.py', 'Test_HTMLTestRunner']
    unittest.main(argv=argv)
    # Testing HTMLTestRunner with HTMLTestRunner would work. But instead
    # we will use standard library's TextTestRunner to reduce the nesting
    # that may confuse people.
    #HTMLTestRunner.main(argv=argv)

