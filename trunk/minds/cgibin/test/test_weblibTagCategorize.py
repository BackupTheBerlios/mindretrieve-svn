# -*- coding: utf-8 -*-
import sys
import unittest
import urllib

from minds.safe_config import cfg as testcfg
from minds.cgibin.test import test_weblib
from minds import weblib
from minds.weblib import store


class TestWeblibTagCategorize(test_weblib.TestCGIBase):

  def test_GET(self):
    self.checkPathForPattern("/weblib/tag_categorize", [
        '<html>', 'Categorize tags', '</html>',
    ])


  def test_POST(self):
    test_data = 'a\r\n  b'
    self.checkPathForPattern('/weblib/tag_categorize?category_description=' + urllib.quote(test_data) + '&method=POST', [
        'HTTP/1.0 302 Found',
        'location: /weblib/tag_categorize',
    ])
    wlib = store.getWeblib()
    self.assertEqual(wlib.category.getDescription(), test_data)


if __name__ == '__main__':
    unittest.main()