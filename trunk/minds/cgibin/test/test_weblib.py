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


test_path = testcfg.getpath('testDoc')/'test_weblib/weblib.dat'

class TestCGIBase(unittest.TestCase):

  def setUp(self):
    self.store = store.Store()
    self.TESTTEXT = file(test_path,'rb').read()
    self.store.load('*test*weblib*', StringIO.StringIO(self.TESTTEXT))
    self.wlib = self.store.wlib

    # so that cgi can access it
    store.store_instance = self.store


  def _run_url(self, path):
    """ Invoke the URL and return the response HTTP message """
    buf = fileutil.aStringIO()
    app_httpserver.handlePath(path, buf)
    return buf.getvalue()


  # TODO: we have switched from checkPatterns() to checkStrings(). Clean up the code below.
  def checkPathForPattern(self, path, patterns, no_pattern=None):
    data = self._run_url(path)
    p = patterns_tester.checkStrings(data, patterns, no_pattern)
    msg = (p == no_pattern) and 'unexpected pattern found' or 'pattern missing'
    self.assert_(not p,
        'failed:%s\n  %s: %s%s' % (path, msg, p,
            patterns_tester.showFile(StringIO.StringIO(data), 'out', 10240),
    ))


class TestWeblibCGI(TestCGIBase):

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


  def test_weblib_go_invalid(self):
    self.checkPathForPattern("/weblib/987654321/go;url", [
        '404 not found',
        '987654321 not found',
    ])


  def test_weblib_input_escape(self):
    txt = self._run_url("/weblib?query=</bad_tag>")
    self.assert_('bad_tag' in txt)
    self.assert_('</bad_tag>' not in txt)


  def test_weblib_input_escape_tag(self):
    txt = self._run_url("/weblib?tag=</bad_tag>")
    self.assert_('bad_tag' in txt)
    self.assert_('</bad_tag>' not in txt)


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


if __name__ == '__main__':
    unittest.main()