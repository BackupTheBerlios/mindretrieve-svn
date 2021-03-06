﻿# -*- coding: utf-8 -*-
import sys
import unittest
import urllib

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
    self.assertEqual(len(wlib.tags),6)
    self.failIf(query_wlib.find_url(wlib,'http://abc.com/'))

    # PUT new form
    self.checkPathForPattern('/weblib/_?' + urllib.urlencode({
            'method': 'PUT',
            'url': 'http://abc.com/',
            'title': 'Test Title',
            'tags': 'new tag1, new tag2',
            'create_tags': '1',
        }),[
        'HTTP/1.0 302 Found',
        'location: /updateParent',
    ])

    # one item has added
    self.assertEqual(len(wlib.webpages),6)
    self.assertEqual(len(wlib.tags),8)
    self.assert_(query_wlib.find_url(wlib,'http://abc.com/'))


  def test_PUT_existing(self):
    wlib = store.getWeblib()
    self.assertEqual(len(wlib.webpages),5)
    item = wlib.webpages.getById(1)
    self.assertEqual(item.name, 'MindRetrieve - Search Your Personal Web')

    # PUT form
    self.checkPathForPattern('/weblib/1?' + urllib.urlencode({
            'method': 'PUT',
            'url': 'http://www.mindretrieve.net/',
            'title': 'Test Title',
            'description': 'some description',
            'created': '1902',
            'modified': '1900',
            'lastused': '1901',
            'tags': 'Kremlin, English',
            'nickname': '_nickname_',
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
    self.assertEqual(item.created    , '1902')
#    self.assertEqual(item.modified   , '1900')
#    self.assertEqual(item.lastused   , '1901')
    tags = ','.join(sorted(tag.name.lower() for tag in item.tags))
    self.assertEqual(tags, 'english,kremlin')
    self.assertEqual(item.nickname, '_nickname_')

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
    self.assertEqual(item.created    , '1902')
#    self.assertEqual(item.modified   , '1900')
#    self.assertEqual(item.lastused   , '1901')
    tags = ','.join(sorted(tag.name.lower() for tag in item.tags))
    self.assertEqual(tags, 'english,kremlin')
    self.assertEqual(item.nickname, '_nickname_')


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


  def test_PUT_input_escape(self):
    url = '/weblib/_?' + urllib.urlencode({
            'method': 'PUT',
            'title': '</bad_tag>',
            'description': '</bad_tag>',
            'url': '</bad_tag>',
            'tags': '</bad_tag>',
            'create_tags': '',
        })
    txt = self._run_url(url)
    self.assert_('bad_tag' in txt)
    self.assert_('</bad_tag>' not in txt)


  def test_PUT_char_workout(self):
    # test_PUT_input_escape() is a quick basic test
    # this one is going to give character escaping a good work out
    url = '/weblib/_?' + urllib.urlencode({
            'method': 'PUT',
            'title': u'€!"#$%&\'()*+,-. /0123456789: ;<=>?@[\\]^_`{|}~'.encode('utf8'),
            'description': u'description:€!"#$%&\'()*+,-. /0123456789: ;<=>?@[\\]^_`{|}~\r\n[For testing]'.encode('utf8'),
            'url': u'url:€!"#$%&\'()*+,-. /0123456789: ;<=>?@[\\]^_`{|}~'.encode('utf8'),
            'tags': u'€!"$% &\'()*-./; =?[\\]^ _`{|}~'.encode('utf8'),
            'create_tags': '1'
        })
    self.checkPathForPattern(url,[
        'HTTP/1.0 302 Found',
        'location: /updateParent',
    ])

    # one item has added
    wlib = store.getWeblib()
    tag = wlib.tags.getByName(u'€!"$% &\'()*-./; =?[\\]^ _`{|}~')
    self.assert_(tag)

    lastId = wlib.webpages._lastId      # undocumented
    page = wlib.webpages.getById(lastId)
    self.assert_(page)
    self.assertEqual(page.name,        u'€!"#$%&\'()*+,-. /0123456789: ;<=>?@[\\]^_`{|}~')
    self.assertEqual(page.description, u'description:€!"#$%&\'()*+,-. /0123456789: ;<=>?@[\\]^_`{|}~\r\n[For testing]')
    self.assertEqual(page.url,         u'url:€!"#$%&\'()*+,-. /0123456789: ;<=>?@[\\]^_`{|}~')
    self.assertEqual(page.tags,        [tag])


if __name__ == '__main__':
    unittest.main()