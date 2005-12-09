# -*- coding: utf-8 -*-
import sys
import unittest

from minds.safe_config import cfg as testcfg
from minds.cgibin.test import test_weblib
from minds import weblib
from minds.weblib import store


class TestWeblibMultiForm(test_weblib.TestCGIBase):

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


if __name__ == '__main__':
    unittest.main()