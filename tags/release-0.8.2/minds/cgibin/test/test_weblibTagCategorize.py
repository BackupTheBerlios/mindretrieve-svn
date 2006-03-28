# -*- coding: utf-8 -*-
import sys
import unittest
import urllib

from minds.safe_config import cfg as testcfg
from minds.cgibin.test import test_weblib
from minds import weblib


class TestWeblibTagCategorize(test_weblib.TestCGIBase):

  def test_GET(self):
    self.checkPathForPattern("/weblib/tag_categorize", [
        '<html>', 'Categorize Tags', '</html>',
    ])


  def test_POST0(self):
    self.checkPathForPattern('/weblib/tag_categorize?category_description=&method=POST', [
        'HTTP/1.0 302 Found',
        'location: /weblib',
    ])
    self.assertEqual(self.wlib.category.getDescription(), '')


  def test_POST(self):
    test_data = 'a\r\n  b'
    self.checkPathForPattern('/weblib/tag_categorize?category_description=' + urllib.quote(test_data) + '&method=POST', [
        'HTTP/1.0 302 Found',
        'location: /weblib',
    ])
    self.assertEqual(self.wlib.category.getDescription(), test_data)


  def test_POST_illegal(self):
    test_data = '@bad1\r\n#bad2\r\ngood'
    self.checkPathForPattern('/weblib/tag_categorize?category_description=' + urllib.quote(test_data) + '&method=POST', [
        'HTTP/1.0 302 Found',
        'location: /weblib',
    ])

    # no error. But illegal characters got converted to '?'
    wlib = self.wlib
    self.assertEqual(wlib.category.getDescription(), '.bad1\r\n.bad2\r\ngood')
    self.assert_(wlib.tags.getByName('.bad1'))
    self.assert_(wlib.tags.getByName('.bad2'))
    self.assert_(wlib.tags.getByName('good'))


  def test_POST_input_escape(self):
    # First insert some risky data into weblib
    badtag = weblib.Tag(name='</bad_tag>')
    badtag = self.store.writeTag(badtag)
    badpage = weblib.WebPage(
        name        = '</bad_tag>',
        url         = '</bad_tag>',
        description = '</bad_tag>',
        tags        = [badtag]
    )
    badpage = self.store.writeWebPage(badpage)

    # GET and make sure it is escaped
    txt = self._run_url('/weblib/tag_categorize')
    self.assert_('bad_tag' in txt)
    self.assert_('</bad_tag>' not in txt)


if __name__ == '__main__':
    unittest.main()