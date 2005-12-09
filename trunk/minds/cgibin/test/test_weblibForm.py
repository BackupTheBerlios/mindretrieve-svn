# -*- coding: utf-8 -*-
import sys
import unittest
import urllib

from minds.safe_config import cfg as testcfg
from minds.cgibin.test import test_weblib
from minds import weblib
from minds.weblib import query_wlib

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
    wlib = self.wlib
    self.assertEqual(len(wlib.webpages),5)
    self.failIf(query_wlib.find_url(wlib,'http://abc.com/'))

    # PUT new form
    self.checkPathForPattern('/weblib/_?' + urllib.urlencode({
            'method': 'PUT',
            'url': 'http://abc.com/',
            'title': 'Test Title',
        }),[
        'HTTP/1.0 302 Found',
        'location: /updateParent',
    ])

    # one item has added
    self.assertEqual(len(wlib.webpages),6)
    self.assert_(query_wlib.find_url(wlib,'http://abc.com/'))


  def test_PUT_existing(self):
    wlib = self.wlib
    self.assertEqual(len(wlib.webpages),5)
    item = wlib.webpages.getById(1)
    self.assertEqual(item.name, 'MindRetrieve - Search Your Personal Web')

    # PUT form
    self.checkPathForPattern('/weblib/1?' + urllib.urlencode({
            'method': 'PUT',
            'url': 'http://www.mindretrieve.net/',
            'title': 'Test Title',
            'description': 'some description',
            'modified': '1900',
            'lastused': '1901',
            'cached': '1902',
            'tags': 'Kremlin, English',
        }),[
        'HTTP/1.0 302 Found',
        'location: /updateParent',
    ])

    # one item has changed
    self.assertEqual(len(wlib.webpages),5)
    item = wlib.webpages.getById(1)
    self.assertEqual(item.name       , 'Test Title')
    self.assertEqual(item.description, 'some description')
    self.assertEqual(item.url        , 'http://www.mindretrieve.net/')
    self.assertEqual(item.modified   , '1900')
    self.assertEqual(item.lastused   , '1901')
#    self.assertEqual(item.cached     , '1902')
    tags = ','.join(sorted(tag.name.lower() for tag in item.tags))
    self.assertEqual(tags, 'english,kremlin')

    # PUT partial parameters (only URL)
    self.checkPathForPattern('/weblib/1?' + urllib.urlencode({
            'method': 'PUT',
            'url': 'new url',
        }),[
        'HTTP/1.0 302 Found',
        'location: /updateParent',
    ])

    # url has changed
    item = wlib.webpages.getById(1)
    self.assertEqual(item.url        , 'new url')
    # the rest is unchanged
    self.assertEqual(item.name       , 'Test Title')
    self.assertEqual(item.description, 'some description')
    self.assertEqual(item.modified   , '1900')
    self.assertEqual(item.lastused   , '1901')
#    self.assertEqual(item.cached     , '1902')
    tags = ','.join(sorted(tag.name.lower() for tag in item.tags))
    self.assertEqual(tags, 'english,kremlin')


  def test_PUT_illegal(self):
    # PUT illegal tag
    self.checkPathForPattern('/weblib/_?' + urllib.urlencode({
            'method': 'PUT',
            'url': 'http://www.mindretrieve.net/',
            'title': 'Test Title',
            'tags': '#illegal tag',
        }),[
        '<html>',
        'These characters are not allowed',
        '#illegal',
        '</html>',
    ])

    # PUT new tag
    self.checkPathForPattern('/weblib/_?' + urllib.urlencode({
            'method': 'PUT',
            'url': 'http://www.mindretrieve.net/',
            'title': 'Test Title',
            'tags': 'this is a new tag',
        }),[
        '<html>',
        'These tags are not previous used',
        'this is a new tag',
        '</html>',
    ])

if __name__ == '__main__':
    unittest.main()