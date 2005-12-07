# -*- coding: utf-8 -*-
import datetime
import sets
import StringIO
import sys
import unittest

from minds.safe_config import cfg as testcfg
from minds import weblib
from minds.weblib import store

testpath = testcfg.getpath('testDoc')


class TestStore(unittest.TestCase):

    TESTFILE_PATH = testpath/'test_weblib/weblib.dat'

    def setUp(self):
        self.store = store.Store()
        self.buf = StringIO.StringIO()
        self.store.load('*test*buffer*', self.buf)


    def tearDown(self):
        pass


    def _make_test_data(self):
        store = self.store
        wlib = store.wlib
        store.writeTag(weblib.Tag(name='def_tag1'))
        store.writeTag(weblib.Tag(name='def_tag2'))
        store.writeTag(weblib.Tag(name='def_tag3'))
        self.assertEqual(wlib.tags.getById(1).name, 'def_tag1')
        store.writeWebPage(weblib.WebPage(name='def_page1'))
        store.writeWebPage(weblib.WebPage(name='def_page2'))
        store.writeWebPage(weblib.WebPage(name='def_page3'))
        self.assertEqual(wlib.webpages.getById(1).name, 'def_page1')
        self.assertEqual((3, 3), (len(wlib.tags), len(wlib.webpages)))


    def _load_TESTFILE(self):
        self.TESTTEXT = file(self.TESTFILE_PATH,'rb').read()
        self.buf = StringIO.StringIO(self.TESTTEXT)
        self.store.load('*test*weblib*', self.buf)


    def _assert_weblib_size(self, nt, nw):
        self.assertEqual(len(self.store.wlib.tags), nt)
        self.assertEqual(len(self.store.wlib.webpages), nw)


    def test_init(self):
        self._assert_weblib_size(0, 0)


    def test_write_header(self):
        wlib = self.store.wlib
        self._make_test_data()

        # before
        self.assertEqual(wlib.headers['encoding'], 'utf8')
        self.assertEqual(wlib.headers.get('test','?'), '?')
        nt, nw = len(wlib.tags), len(wlib.webpages)

        # write
        self.store.writeHeader('encoding', 'new')
        self.store.writeHeader('test', '123')

        # after
        self.assertEqual(wlib.headers['encoding'], 'new')
        self.assertEqual(wlib.headers.get('test','?'), '123')
        self._assert_weblib_size(nt, nw)


    def test_write_tag_new(self):
        wlib = self.store.wlib
        self._make_test_data()

        # before
        nt, nw = len(wlib.tags), len(wlib.webpages)
        self.assertTrue('Tag1' not in self.buf.getvalue())

        # write
        tag = weblib.Tag(name='Tag1')
        self.assertTrue(tag.id == -1)
        newTag = self.store.writeTag(tag)

        # after
        self._assert_weblib_size(nt+1, nw)
        self.assertTrue('Tag1' in self.buf.getvalue())

        self.assertTrue(newTag.id >= 0)
        t = wlib.tags.getByName('tag1')
        self.assertTrue(t)
        self.assertTrue(t.id == newTag.id)

        # before
        self.assertTrue(not wlib.tags.getById(10))

        # write webpage with new id assigned
        tag = weblib.Tag(id=10, name='Tag10')
        newTag = self.store.writeTag(tag)

        # verify
        self._assert_weblib_size(nt+2, nw)
        self.assertEqual(wlib.tags.getById(10).name, 'Tag10')


    def test_write_tag_existing(self):
        wlib = self.store.wlib
        self._make_test_data()

        # before
        nt, nw = len(wlib.tags), len(wlib.webpages)
        self.assertTrue('new tag1' not in self.buf.getvalue())
        self.assertTrue(wlib.tags.getByName('def_tag1'))

        # write
        tag = weblib.Tag(id=1, name='new tag1')
        self.store.writeTag(tag)

        # after
        self._assert_weblib_size(nt, nw)
        self.assertTrue('new tag1' in self.buf.getvalue())
        self.assertTrue(not wlib.tags.getByName('def_tag1'))
        self.assertTrue(wlib.tags.getByName('new tag1'))


    def test_write_webpage_new(self):
        wlib = self.store.wlib
        self._make_test_data()

        # before
        nt, nw = len(wlib.tags), len(wlib.webpages)
        self.assertTrue('Page1' not in self.buf.getvalue())

        # write
        page = weblib.WebPage(name='Page1')
        self.assertTrue(page.id == -1)
        newPage = self.store.writeWebPage(page)

        # after
        self._assert_weblib_size(nt, nw+1)
        self.assertTrue('Page1' in self.buf.getvalue())
        self.assertTrue(newPage.id >= 0)
        self.assertTrue(wlib.webpages.getById(newPage.id))

        # before
        self.assertTrue(not wlib.webpages.getById(10))

        # write webpage with new id assigned
        page = weblib.WebPage(id=10, name='Page10')
        newPage = self.store.writeWebPage(page)

        # verify
        self._assert_weblib_size(nt, nw+2)
        self.assertEqual(wlib.webpages.getById(10).name, 'Page10')


    def test_write_webpage_existing(self):
        wlib = self.store.wlib
        self._make_test_data()

        # before
        nt, nw = len(wlib.tags), len(wlib.webpages)
        self.assertTrue('new page1' not in self.buf.getvalue())
        self.assertTrue(wlib.webpages.getById(1).name, 'def_tag1')

        # write
        tag = weblib.Tag(id=1, name='new page1')
        self.store.writeTag(tag)

        # after
        self._assert_weblib_size(nt, nw)
        self.assertTrue(wlib.webpages.getById(1).name, 'new tag1')
        self.assertTrue('new page1' in self.buf.getvalue())


    def test_remove_tag(self):
        wlib = self.store.wlib
        self._make_test_data()

        # before
        nt, nw = len(wlib.tags), len(wlib.webpages)
        self.assertTrue('r!@1' not in self.buf.getvalue())

        # remove
        self.store.removeItem(wlib.tags.getById(1))

        # after
        self._assert_weblib_size(nt-1, nw)
        self.assertEqual(wlib.tags.getById(1), None)
        self.assertTrue('r!@1' in self.buf.getvalue())


    def test_remove_webpage(self):
        wlib = self.store.wlib
        self._make_test_data()

        # before
        nt, nw = len(wlib.tags), len(wlib.webpages)
        self.assertTrue('r!1' not in self.buf.getvalue())

        # remove
        self.store.removeItem(wlib.webpages.getById(1))

        # after
        self._assert_weblib_size(nt, nw-1)
        self.assertTrue('r!1' in self.buf.getvalue())
        self.assertEqual(wlib.webpages.getById(1), None)


    def test_load0(self):
        self.store.load('empty file', StringIO.StringIO(''))
        wlib = self.store.wlib
        self._assert_weblib_size(0,0)


    def test_load(self):
        # Load the test file. Note that 4 languages are used in the test data.
        self._load_TESTFILE()

        wlib = self.store.wlib
        self._assert_weblib_size(6,5)

        # test all tags are retrieved
        tag_names = sorted([t.name for t in wlib.tags])
        test_tags = sorted([
            u'inbox',
            u'Русский',
            u'Français',
            u'日本語',
            u'Kremlin',
            u'English',
        ])
        self.assertEqual( tag_names, test_tags)

        # test all URLs match
        # URL is the last field in the file.
        # If they matches then the order of fields is likely right.
        urls = sorted([item.url for item in wlib.webpages])
        test_urls = sorted([
            u'http://www.mindretrieve.net/',
            u'http://ru.wikipedia.org/wiki/Московский_Кремль',
            u'http://fr.wikipedia.org/wiki/Kremlin_de_Moscou',
            u'http://ja.wikipedia.org/wiki/クレムリン',
            u'http://en.wikipedia.org/wiki/Moscow_Kremlin',
        ])
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
        self.assertEqual(tags, test_tags)


    def test_load_n_save(self):
        # Assert that load and then save would result in identical file
        # This is actually not a sure thing
        # - output may contain time sensitive information
        # - The test weblib.dat is hand edited and may contain artifacts like extra blank lines
        # We can do one more round of load-save to circumvent the last problem though

        self._load_TESTFILE()
        output = StringIO.StringIO()
        self.store.save('*output*buffer*', output)

        #print >>sys.stderr, output.getvalue()

        fp0 = StringIO.StringIO(self.TESTTEXT)
        iter0 = enumerate(fp0)
        output.seek(0)
        for lineno, line0 in iter0:
            while line0.startswith('date:'):
                lineno, line0 = iter0.next()        # don't match date header
            line1 = output.next()
            while line1.startswith('date:'):
                line1 = output.next()               # don't match date header

            # compare it line by line so error is easier to spot
            line0 = line0.rstrip()
            line1 = line1.rstrip()
            self.assertEqual(line0, line1, 'line %s\nfile0: %s\nfile1: %s' % (lineno+1,
                line0.encode('string_escape'),
                line1.encode('string_escape'),
            ))

        # output is drained
        self.assertRaises(StopIteration, output.next)


    def _check_changed(self):
        # verify the changes made in test_change_n_save()
        #print >>sys.stderr, self.store
        wlib = self.store.wlib
        self._assert_weblib_size(7, 4)
        self.assertEqual(wlib.headers['category_description'], 'Kremlin')
        self.assertTrue(wlib.tags.getByName('tag1'))
        self.assertTrue(wlib.tags.getByName('tag2'))
        self.assertTrue(not wlib.tags.getByName('English'))
        self.assertTrue(not wlib.webpages.getById(2))


    def test_change_n_save(self):
        # change wlib and generates change records
        # reload the changed data file to ensure changes are playback correctly
        # similarly test the saved snapshot data file
        self._load_TESTFILE()
        self._assert_weblib_size(6, 5)
        wlib = self.store.wlib

        # change header
        self.store.writeHeader('category_description', 'Kremlin')

        # add tag
        tag1 = weblib.Tag(name='tag1')
        self.store.writeTag(tag1)

        # modify tag
        tag_english = wlib.tags.getByName('English')
        tag2 = tag_english.__copy__()
        tag2.name = 'tag2'
        self.store.writeTag(tag2)

        # delete webpage
        item2 = wlib.webpages.getById(2)
        self.store.removeItem(item2)

        self._check_changed()

        # this is the changed data file
        changed_data = self.buf.getvalue()
        # changed data file have records appended to TESTTEXT
        self.assertTrue( changed_data.startswith(self.TESTTEXT))

        # reload changed data file
        old_weblib = self.store.wlib
        self.store.load('*changed*buffer*', StringIO.StringIO(changed_data))
        self.assertTrue(self.store.wlib is not old_weblib)  # a new wlib is really loaded :)
        self._check_changed()

        # save data file snapshot
        buf = StringIO.StringIO()
        self.store.save('*snapshot*buffer*', buf)
        snapshot_data = buf.getvalue()
        # unlike changed data snapshot save records without change records
        self.assertTrue( not snapshot_data.startswith(self.TESTTEXT))

        # load snapshot and verify
        old_weblib = self.store.wlib
        self.store.load('*snapshot*buffer*', StringIO.StringIO(snapshot_data))
        self.assertTrue(self.store.wlib is not old_weblib)  # a new wlib is really loaded :)
        self._check_changed()


    def test_timestamp(self):
        ts = store._getTimeStamp()
        self.assertTrue(len(ts) == len('1234-06-18 12:34:56'))
        d = store._parseTimeStamp(ts)
        self.assertTrue(d <= datetime.datetime.now())


    def test_invalid_timestamp(self):
        dt = store._parseTimeStamp('1234-06-18 12:34:56')
        self.assertEqual(dt, datetime.datetime(1234,6,18,12,34,56))

        self.assertRaises( ValueError, store._parseTimeStamp, '')
        self.assertRaises( ValueError, store._parseTimeStamp, '1234-06-18 12:34:56Z')
        self.assertRaises( ValueError, store._parseTimeStamp, '1234/06/18 12:34:56')
        self.assertRaises( ValueError, store._parseTimeStamp, 'abcd-06-18 12:34:56')
        self.assertRaises( ValueError, store._parseTimeStamp, '9999-99-99 99:99:99')


if __name__ == '__main__':
    unittest.main()
