# -*- coding: utf-8 -*-
import sys
import unittest

from minds.safe_config import cfg as testcfg
from minds.cgibin.test import test_weblib
from minds import weblib
from minds.weblib import query_wlib
from minds.weblib import store

class TestWeblibForm(test_weblib.TestCGIBase):

  def test_GET_404(self):
    self.checkPathForPattern("/weblib/987654321", [
        '404 not found', '987654321 not found',
    ])


  def test_GET_rid(self):
    self.checkPathForPattern("/weblib/4", [
        '<html>', 'Edit Entry', 'ja.wikipedia.org', '</html>',
    ])
    self.checkPathForPattern("/weblib/4/form", [
        '<html>', 'Edit Entry', 'ja.wikipedia.org', '</html>',
    ])


  def test_GET_new(self):
    self.checkPathForPattern("/weblib/_", [
        '<html>', 'Add Entry', '/weblib/_', '</html>',
    ])
    self.checkPathForPattern("/weblib/_/form", [
        '<html>', 'Add Entry', '/weblib/_', '</html>',
    ])


  def test_GET_URL_match(self):
    # note URL http://en.wikipedia.org/wiki/Moscow_Kremlin match id 5.
    url = '/weblib/_?url=http://en.wikipedia.org/wiki/Moscow_Kremlin&title=1+2&description='
    new_url = url.replace('/_','/5')
    self.checkPathForPattern(url, [
        '302 Found',
        'location: ' + new_url,
    ])


  def test_PUT_404(self):
    self.checkPathForPattern("/weblib/987654321?method=PUT", [
        '404 not found', '987654321 not found',
    ])


  def test_PUT_new(self):
    wlib = store.getWeblib()
    self.assertEqual(len(wlib.webpages),5)
    self.failIf(query_wlib.find_url(wlib,'http://abc.com'))

    # PUT new form
    self.checkPathForPattern("/weblib/_?method=PUT&url=http%3A%2F%2Fabc.com%2F&title=Test%20Title", [
        'HTTP/1.0 302 Found',
        'location: /updateParent',
    ])

    # one item has added
    self.assertEqual(len(wlib.webpages),6)
    self.assert_(query_wlib.find_url(wlib,'http://abc.com/'))


  def test_PUT_rid(self):
    wlib = store.getWeblib()
    self.assertEqual(len(wlib.webpages),5)
    item = wlib.webpages.getById(1)
    self.assertEqual(item.name, 'MindRetrieve - Search Your Personal Web')

    # PUT form
    self.checkPathForPattern("/weblib/1?method=put&url=http%3A%2F%2Fwww.mindretrieve.net%2F&title=Test%20Title", [
        'HTTP/1.0 302 Found',
        'location: /updateParent',
    ])

    # one item has changed
    self.assertEqual(len(wlib.webpages),5)
    item = wlib.webpages.getById(1)
    self.assertEqual(item.name, 'Test Title')


if __name__ == '__main__':
    unittest.main()