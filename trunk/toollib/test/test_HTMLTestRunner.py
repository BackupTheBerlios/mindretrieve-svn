# -*- coding: latin-1 -*-

import datetime
import string
import StringIO
import sys
import time
import unittest
import HTMLTestRunner
from xml.sax import saxutils


# ----------------------------------------------------------------------
# Sample tests to drive the HTMLTestRunner

class SampleCase1(unittest.TestCase):
    def test_10(self):
        print >>sys.stderr, 'some info to stderr in 10'

    def test_11_fail(self):
        self.fail('test failed')

    def test_12_error(self):
        raise RuntimeError('some problem happened in 12')

class SampleCase2(SampleCase1):
    # 3 cases from SampleCase1
    def test_23(self):
        pass

class SampleCase3(unittest.TestCase):
    def test_30(self):
        pass


class SampleCase4(unittest.TestCase):
    """ Similiar to SampleCase1 with everything in unicode """

    MESSAGE = u'the message is \u8563'

    def test_40(self):
        print self.MESSAGE
        print >>sys.stderr, self.MESSAGE

    def test_41_fail(self):
        self.fail(self.MESSAGE)

    def test_42_error(self):
        raise RuntimeError(self.MESSAGE)


class SampleCase5(unittest.TestCase):
    """ Similiar to SampleCase1 with everything in latin-1 """

    MESSAGE = 'the message is áéíóú'

    def test_50(self):
        print self.MESSAGE
        print >>sys.stderr, self.MESSAGE

    def test_51_fail(self):
        self.fail(self.MESSAGE)

    def test_52_error(self):
        raise RuntimeError(self.MESSAGE)


# ------------------------------------------------------------------------
# This is the main test on HTMLTestRunner

class Test_HTMLTestRunner(unittest.TestCase):

    # Define the expected output sequence. This is imperfect but should
    # give a good sense of the well being of the test.
    #
    # General format
    # 1. test name
    # 2. status
    # 3. output captured
    EXPECTED = unicode("""
>test_10<
>pass<
some info to stderr in 10

>test_11_fail<
>fail<

>test_12_error<
>error<
some problem happened in 12

>test_23<
>pass<

>test_30<
>pass<

>test_40<
>pass<

>test_41_fail<
>fail<
AssertionError:

>test_42_error<
>error<
RuntimeError:

>test_50<
>pass<
the message is áéíóú\nthe message is áéíóú

>test_51_fail<
>fail<
AssertionError: the message is áéíóú

>test_52_error<
>error<
RuntimeError: the message is áéíóú

Total
>14<
>6<
>4<
>4<
</html>
""",'latin-1')


    def setUp(self):
        self.suite = unittest.TestSuite()
        self.suite.addTests([
            unittest.defaultTestLoader.loadTestsFromTestCase(SampleCase1),
            unittest.defaultTestLoader.loadTestsFromTestCase(SampleCase2),
            unittest.defaultTestLoader.loadTestsFromTestCase(SampleCase3),
            unittest.defaultTestLoader.loadTestsFromTestCase(SampleCase4),
            unittest.defaultTestLoader.loadTestsFromTestCase(SampleCase5),
            ])


    def test1(self):
        buf = StringIO.StringIO()
        #unittest baseline
        #runner = unittest.TextTestRunner(buf)
        runner = HTMLTestRunner.HTMLTestRunner(buf)
        runner.run(self.suite)
        byte_output = buf.getvalue()
        print byte_output
        self._checkoutput(byte_output.decode('utf-8'))


    def _checkoutput(self,output):
        i = 0
        for p in self.EXPECTED.splitlines():
            if not p:
                continue
            j = output.find(p,i)
            if j < 0:
                self.fail('Pattern not found %s' % p)
            i = j + len(p)




##############################################################################
# Executing this module from the command line
##############################################################################

import unittest
if __name__ == "__main__":
    argv=['test_HTMLTestRunner.py', 'Test_HTMLTestRunner']
    unittest.main(argv=argv)
    # Testing HTMLTestRunner with HTMLTestRunner would work. But instead
    # we will use standard library's TextTestRunner to reduce the nesting
    # that may confuse people.
    #HTMLTestRunner.main(argv=argv)

