import datetime
import string
import StringIO
import sys
import time
import unittest
import HTMLTestRunner
from xml.sax import saxutils


# ----------------------------------------------------------------------
# Sample tests to test HTMLTestRunner

class SampleCase1(unittest.TestCase):
    def test_0(self):
        print 'running test_0'
        print >>sys.stderr, 'some info to stderr'
    def test_1(self):
        self.fail('test failed')
    def test_2(self):
        raise RuntimeException('some problem happened')

class SampleCase2(SampleCase1):
    # 3 cases from SampleCase1
    def test_23(self):
        pass

class SampleCase3(unittest.TestCase):
    def test_30(self):
        pass
    
class SelfTest(unittest.TestCase):
    def setUp(self):
        self.suite = unittest.TestSuite()
        self.suite.addTests([SampleCase1,SampleCase2,SampleCase3])
        
    def test1(self):
        buf = StringIO.StringIO()
        runner = HTMLTestRunner.HTMLTestRunner(buf)
        runner.run(self.suite)
        print buf
            
##############################################################################
# Executing this module from the command line
##############################################################################

if __name__ == "__main__":
#    HTMLTestRunner.main(['toollib.TestHTMLRunner.SelfTest'])
    HTMLTestRunner.main(module=None)

