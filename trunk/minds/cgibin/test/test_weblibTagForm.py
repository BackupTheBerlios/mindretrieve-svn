# -*- coding: utf-8 -*-
import sys
import unittest

from minds.safe_config import cfg as testcfg
from minds.cgibin.test import test_weblib
from minds import weblib
from minds.weblib import store


class TestTagForm(test_weblib.TestCGIBase):

  def test_GET(self):
    self.checkPathForPattern("/weblib/@124/form", [
        '<html>', 'Edit Tag', 'Kremlin', '</html>',
    ])

  def test_GET_404(self):
    self.checkPathForPattern("/weblib/@987654321", [
        '404 not found',
        '@987654321 not found',
    ],
    no_pattern='html'
    )

  def test_POST_404(self):
    self.checkPathForPattern("/weblib/@987654321/form?method=POST&name=Buckingham", [
        '404 not found',
        '@987654321 not found',
    ])

  def test_POST_rename(self):
    wlib = store.getWeblib()

    # before
    page = wlib.webpages.getById(2)
    tag = wlib.tags.getByName('Kremlin')
    self.assertEqual(len(wlib.tags),6)
    self.assertEqual(tag.name, 'Kremlin')
    self.assertTrue(tag in page.tags)
    self.assertTrue(not wlib.tags.getByName('Buckingham'))
    self.assertTrue('Buckingham' not in wlib.category.getDescription())

    self.checkPathForPattern("/weblib/@124/form?method=POST&name=Buckingham", [
        'HTTP/1.0 302 Found',
        'location: /updateParent',
    ])

    # after
    page = wlib.webpages.getById(2)
    tag = wlib.tags.getByName('Buckingham')
    self.assertEqual(len(wlib.tags),6)
    self.assertEqual(tag.name, 'Buckingham')
    self.assertTrue(tag in page.tags)
    self.assertTrue(not wlib.tags.getByName('Kremlin'))
    self.assertTrue('Buckingham' in wlib.category.getDescription())


  def test_POST_rename_capitalization(self):
    wlib = store.getWeblib()

    # before
    page = wlib.webpages.getById(2)
    tag = wlib.tags.getByName('Kremlin')
    self.assertEqual(len(wlib.tags),6)
    self.assertEqual(tag.name, 'Kremlin')
    self.assertTrue(tag in page.tags)

    self.checkPathForPattern("/weblib/@124/form?method=POST&name=KREMLIN", [
        'HTTP/1.0 302 Found',
        'location: /updateParent',
    ])

    # after
    page = wlib.webpages.getById(2)
    tag = wlib.tags.getByName('Kremlin')
    self.assertEqual(len(wlib.tags),6)
    self.assertEqual(tag.name, 'KREMLIN')
    self.assertTrue(tag in page.tags)


  def test_POST_merge(self):
    wlib = store.getWeblib()

    # before
    page = wlib.webpages.getById(2)
    self.assertEqual(len(wlib.tags),6)
    self.assertTrue(wlib.tags.getByName('Kremlin'))
    self.assertTrue(wlib.tags.getByName('inbox') not in page.tags)

    self.checkPathForPattern("/weblib/@124/form?method=POST&name=inbox", [
        'HTTP/1.0 302 Found',
        'location: /updateParent',
    ])

    # after
    page = wlib.webpages.getById(2)
    self.assertEqual(len(wlib.tags),5)
    self.assertTrue(not wlib.tags.getByName('Kremlin'))
    self.assertTrue(wlib.tags.getByName('inbox') in page.tags)


  def test_POST_invalid(self):
    self.checkPathForPattern("/weblib/@124/form?method=POST&name=", [
        '200 OK',
        '<html>',
        'Please enter a name',
        '</html>',
    ])

    # spaces only also invalid
    self.checkPathForPattern("/weblib/@124/form?method=POST&name=++", [
        '200 OK',
        '<html>',
        'Please enter a name',
        '</html>',
    ])

    # illegal characters
    self.checkPathForPattern("/weblib/@124/form?method=POST&name=#illegal", [
        '200 OK',
        '<html>',
        'These characters are not allowed in tag name',
        '</html>',
    ])


  def test_PUT_input_escape(self):
    # First insert some risky data into weblib
    badtag = weblib.Tag(name='</bad_tag>')
    badtag = store.getStore().writeTag(badtag)

    # GET
    url = '/weblib/@%s/form?name=</bad_tag>' % badtag.id
    txt = self._run_url(url)
    self.assert_('bad_tag' in txt)
    self.assert_('</bad_tag>' not in txt)


  def test_POST_category_collapse(self):
    wlib = store.getWeblib()

    self.assertTrue('c' not in wlib.tags.getById(124).flags)

    # turn it on
    self.checkPathForPattern("/weblib/@124/form?method=POST&category_collapse=on", [
        '200 OK',
        'setCategoryCollapse @124 True',
    ])
    self.assertTrue('c' in wlib.tags.getById(124).flags)

    # turn it off
    self.checkPathForPattern("/weblib/@124/form?method=POST&category_collapse=", [
        '200 OK',
        'setCategoryCollapse @124 False',
    ])
    self.assertTrue('c' not in wlib.tags.getById(124).flags)

    # turn it off again
    self.checkPathForPattern("/weblib/@124/form?method=POST&category_collapse=", [
        '200 OK',
        'setCategoryCollapse @124 False',
    ])
    self.assertTrue('c' not in wlib.tags.getById(124).flags)


if __name__ == '__main__':
    unittest.main()