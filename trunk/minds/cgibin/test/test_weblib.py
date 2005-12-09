# -*- coding: utf-8 -*-
import datetime
import StringIO
import sys
import unittest
import urllib

from minds.safe_config import cfg as testcfg
from minds import app_httpserver
from minds.cgibin import weblib as weblib_cgi
from minds.util import fileutil
from minds.util import patterns_tester
from minds import weblib
from minds.weblib import query_wlib
from minds.weblib import store


testpath = testcfg.getpath('testDoc')

class TestCGIBase(unittest.TestCase):

  def setUp(self):
    stor = store.getStore()
    testfile_path = testpath/'test_weblib/weblib.dat'
    testdata = file(testfile_path,'rb').read()
    stor.load('*test*data*',StringIO.StringIO(testdata))

  # TODO: we have switched from checkPatterns() to checkStrings(). Clean up the code below.
  def checkPathForPattern(self, path, patterns, no_pattern=None):
    buf = fileutil.aStringIO()
    app_httpserver.handlePath(path, buf)
    buf.seek(0)
    # Beware of the limitation of patterns_tester()
    # It test for string occurance line by line
    p = patterns_tester.checkStrings(buf, patterns, no_pattern)
    msg = (p == no_pattern) and 'unexpected pattern found' or 'pattern missing'
    self.assert_(not p,
        'failed:%s\n  %s: %s%s' % (path, msg, p,
            patterns_tester.showFile(buf, 'out', 10240),
    ))


class TestWeblibCGI(TestCGIBase):

  # ------------------------------------------------------------------------
  # /weblib

  def test_weblib(self):
    self.checkPathForPattern("/weblib", [
        '302 Found',                # redirect user from main page to the default tag
    ])

    self.checkPathForPattern("/weblib?tag=inbox", [
        '<html>',
        'www.mindretrieve.net',     # this entry appears on main page
        '</html>',
    ])

    # controlled test for below
    # ja.wikipedia.org will not be listed unless there is a right query
    self.checkPathForPattern("/weblib?tag=inbox", ['<html>',],
        'ja.wikipedia.org'
    )

    self.checkPathForPattern("/weblib?tag=English", ['<html>',],
        'ja.wikipedia.org'
    )


  def test_weblib_tag(self):
    # this is the URL encoded for the Japanese tag
    self.checkPathForPattern("/weblib?tag=%E6%97%A5%E6%9C%AC%E8%AA%9E", [
        '<html>', 'ja.wikipedia.org', '</html>',
    ])


  def test_weblib_query(self):
    self.checkPathForPattern("/weblib?query=%20-%20Wikipedia", [
        '<html>', 'ja.wikipedia.org', '</html>',
    ])


  def test_weblib_go(self):
    self.checkPathForPattern("/weblib/4/go;url", [
        'HTTP/1.0 302 Found',
        'ja.wikipedia.org',
        ],
        '</html>'
    )


  def _str_cat_nodes(self, cat_nodes):
    strs = []
    for cat, subcat in cat_nodes:
        strs.append(str(cat))
        for node in subcat:
            if node == weblib_cgi.CategoryNode.BEGIN_HIGHLIGHT:
                strs.append('[')
            elif node == weblib_cgi.CategoryNode.END_HIGHLIGHT:
                strs.append(']')
            else:
                strs.append(unicode(node))
    return strs


  def test_buildCategoryList(self):
    cat_nodes = weblib_cgi._buildCategoryList(store.getWeblib(), '')
    self.assertTrue(not cat_nodes[0][0].highlight)
    self.assertEqual(self._str_cat_nodes(cat_nodes), [
        u'Kremlin',
        u'.Русский',
        u'.Français',
        u'.日本語',
        u'.English',
        u'TAG',
        u'inbox',
    ])

    # highlight a top level cat
    cat_nodes = weblib_cgi._buildCategoryList(store.getWeblib(), 'Kremlin')
    self.assertTrue(cat_nodes[0][0].highlight)
    self.assertEqual(self._str_cat_nodes(cat_nodes), [
        u'Kremlin',
        u'.Русский',
        u'.Français',
        u'.日本語',
        u'.English',
        u'TAG',
        u'inbox',
    ])

    # highlight a subcat
    cat_nodes = weblib_cgi._buildCategoryList(store.getWeblib(), 'English')
    self.assertEqual(self._str_cat_nodes(cat_nodes), [
        u'Kremlin',
        u'.Русский',
        u'.Français',
        u'.日本語',
        u'[',
        u'.English',
        u']',
        u'TAG',
        u'inbox',
    ])


class TestWeblibForm(TestCGIBase):

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



class TestWeblibMultiForm(TestCGIBase):

  def test_GET(self):
    self.checkPathForPattern("/weblib/multiform?method=GET&2=on&3=on", [
        '<html>',
        'Московский Кремль — Википедия',    # title
        'Français', # tag
        '</html>',
    ])


  def test_POST_add(self):
    wlib = store.getWeblib()

    # before
    self.assertEqual(len(wlib.webpages.getById(2).tags), 2) # Kremlin, Русский
    self.assertEqual(len(wlib.webpages.getById(3).tags), 2) # Kremlin, Français

    url = ''.join(['/weblib/multiform',
            '?id_list=2%2C3',                   # 2 - Russian, 3 - French
            '&%40122=on&%40122changed=1',       # add Français
            '&%40121=on&%40121changed=',        # Русский unchanged
            '&add_tags=inbox',                  # add inbox
            '&method=POST',
            ])
    self.checkPathForPattern(url, [
        'HTTP/1.0 302 Found',
        'location: /updateParent',
    ])

    # after
    item = wlib.webpages.getById(2)
    tagIds = sorted([t.id for t in item.tags])
    self.assertEqual(tagIds, [120,121,122,124])     # inbox, Русский, Français, Kremlin

    item = wlib.webpages.getById(3)
    tagIds = sorted([t.id for t in item.tags])
    self.assertEqual(tagIds, [120,122,124])         # inbox, Français, Kremlin


  def test_POST_remove(self):
    wlib = store.getWeblib()

    # before
    self.assertEqual(len(wlib.webpages.getById(2).tags), 2) # Kremlin, Русский
    self.assertEqual(len(wlib.webpages.getById(3).tags), 2) # Kremlin, Français

    url = ''.join(['/weblib/multiform',
            '?id_list=2%2C3',                   # 2 - Russian, 3 - French
            '&%40122=&%40122changed=1',         # remove Français
            '&%40121=on&%40121changed=',        # Русский unchanged
            '&add_tags=inbox',
            '&method=POST',
            ])
    self.checkPathForPattern(url, [
        'HTTP/1.0 302 Found',
        'location: /updateParent',
    ])

    # after
    item = wlib.webpages.getById(2)
    tagIds = sorted([t.id for t in item.tags])
    self.assertEqual(tagIds, [120,121,124])     # inbox, Русский, Kremlin

    item = wlib.webpages.getById(3)
    tagIds = sorted([t.id for t in item.tags])
    self.assertEqual(tagIds, [120,124])         # inbox, Kremlin


  def test_POST_add_new_tag(self):
    wlib = store.getWeblib()

    # before
    self.assertEqual(len(wlib.webpages.getById(2).tags), 2) # Kremlin, Русский
    self.assertEqual(len(wlib.webpages.getById(3).tags), 2) # Kremlin, Français

    url = ''.join(['/weblib/multiform',
            '?id_list=2%2C3',                   # 2 - Russian, 3 - French
            '&%40122=on&%40122changed=1',       # add Français
            '&%40121=on&%40121changed=',        # Русский unchanged
            '&add_tags=aNewTag',
            '&method=POST',
            '&create_tags=1',
            ])
    self.checkPathForPattern(url, [
        'HTTP/1.0 302 Found',
        'location: /updateParent',
    ])

    # after
    newTag = wlib.tags.getByName('aNewTag')
    self.assertTrue(newTag)
    self.assertTrue(newTag.id > 124)            # new tag should have a higher id

    # after
    item = wlib.webpages.getById(2)
    tagIds = sorted([t.id for t in item.tags])
    self.assertEqual(tagIds, [121,122,124,newTag.id]) # Русский, Français, Kremlin, aNewTag

    item = wlib.webpages.getById(3)
    tagIds = sorted([t.id for t in item.tags])
    self.assertEqual(tagIds, [122,124,newTag.id])     # Français, Kremlin, aNewTag


class TestWeblibTagCategorize(TestCGIBase):

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



class TestTagForm(TestCGIBase):

  # ------------------------------------------------------------------------
  # tag_naming

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
    wlib = store.getWeblib()

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