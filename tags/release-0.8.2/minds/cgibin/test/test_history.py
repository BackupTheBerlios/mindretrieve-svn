import sys
import unittest
import urllib

from minds.safe_config import cfg as testcfg
from minds.cgibin.test import test_weblib
from minds import weblib
from minds.weblib import query_wlib

class TestHistory(test_weblib.TestCGIBase):

    def test_GET(self):
        self.checkPathForPattern("/history", [
            '<title>', 'History', '</title>', '</html>',
        ])

    def test_query_no_result_needed(self):
        self.fail()

    def test_query_needed(self):
        self.fail()

    def test_indexnow_needed(self):
        self.fail()


if __name__ == '__main__':
    unittest.main()