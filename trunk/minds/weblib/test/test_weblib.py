# -*- coding: utf-8 -*-
import StringIO
import os.path, sys
import sets
import shutil
import unittest

from minds.test.config_help import cfg
from minds import weblib
from minds.weblib import minds_lib
from minds.weblib import store

testdir = os.path.join(cfg.getPath('testDoc'),'.')[:-1]


# rewire store to use the working copy of test weblib.dat
TEST_FILENAME = os.path.join(testdir,'test_weblib/weblib.dat')
TEST_WORK_FILENAME = os.path.join(testdir,'test_weblib/weblib.work.dat')
shutil.copy(TEST_FILENAME, TEST_WORK_FILENAME)
store.useMainBm(TEST_WORK_FILENAME)


class TestWeblib(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass
        
    def test0(self):
        null_fp = StringIO.StringIO('')    
        wlib = minds_lib.load(null_fp)
        self.assertEqual(len(wlib.webpages), 0)
        self.assertEqual(len(wlib.tags), 0)

    def test_load(self):
        wlib = store.getMainBm()
        self.assertEqual(len(wlib.webpages), 5)
        self.assertEqual(len(wlib.tags), 5)
        
        # note that 4 languages are used in the test data
        
        # test all tags are retrieved
        tag_names = [t.name for t in wlib.tags]
        test_tags = [
            u'Русский',
            u'Français',
            u'日本語',
            u'Kremlin',
            u'English',
        ]
        tag_names.sort()
        test_tags.sort()
        self.assertEqual( tag_names, test_tags)

        # test all URLs match
        # URL is the last field in the file. 
        # If they matches then the order of fields is likely right.
        urls = [item.url for item in wlib.webpages]
        test_urls = [
            u'http://www.mindretrieve.net/',
            u'http://ru.wikipedia.org/wiki/Московский_Кремль',
            u'http://fr.wikipedia.org/wiki/Kremlin_de_Moscou',
            u'http://ja.wikipedia.org/wiki/クレムリン',
            u'http://en.wikipedia.org/wiki/Moscow_Kremlin',
        ]
        urls.sort()
        test_urls.sort()
        self.assertEqual(urls, test_urls)

        # test the tag ids (for one sample webpage) are correctly retrieve
        item = wlib.webpages.getById(4)
        self.assertTrue(item)
        self.assertEqual(item.name, u'クレムリン - Wikipedia')
        tags = sets.Set(item.tags)
        test_tags = sets.Set([
            wlib.tags.getByName('Kremlin'),
            wlib.tags.getByName(u'日本語'),
        ])
        self.assertEqual(len(item.tags), 2)
        self.assertEqual(tags, test_tags)


    def test_load_save(self):
        # Assert that load and then save would result in identical file        
        # This is actually not a sure thing
        # - output may contain time sensitive information
        # - The test weblib.dat is hand edited and may contain artifacts like extra blank lines
        # We can do one more round of load-save to circumvent the last problem though
        original = file(TEST_FILENAME, 'rb').read()
        wlib = minds_lib.load(StringIO.StringIO(original))
        buf = StringIO.StringIO()
        minds_lib.save(buf, wlib)

        buf.seek(0)
        for lineno, line0 in enumerate(StringIO.StringIO(original)):
            line1 = buf.next()
            # compare it line by line so error is easier to spot
            line0 = line0.rstrip()
            line1 = line1.rstrip()
            self.assertEqual(line0, line1, 'line %s\nfile0: %s\nfile1: %s' % (lineno+1,
                line0.encode('string_escape'),
                line1.encode('string_escape'),
            ))


if __name__ == '__main__':
    unittest.main()