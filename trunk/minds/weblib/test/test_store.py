# -*- coding: utf-8 -*-
import datetime
import os
import os.path
import sets
import StringIO
import sys
import unittest

from minds.safe_config import cfg as testcfg
from minds import weblib
from minds.weblib import store

testpath = testcfg.getpath('testDoc')


class TestDsvUtil(unittest.TestCase):

    # list of (encoded string, decoded fields)
    DATA = [
    ('',                ['']),                  # 0 field
    (r'a',              ['a']),                 # 1 field
    (r'a|b|c',          ['a','b','c']),         # 3 fields

    (r'|b',             ['','b']),              # start with bar
    (r'a|',             ['a','']),              # end with bar
    (r'a||b',           ['a','','b']),          # consecutive bars
    (r'\x7Ca|b\x7C|\x7Cc\x7C',
                        ['|a','b|','|c|']),     # bars escaped

    (r'\\a|b\\|\\c\\',  ['\\a','b\\','\\c\\']), # slashes escaped
    (r'\\a|\\\x7C|\x7Cc\\',
                        ['\\a','\\|','|c\\']),  # bars and slashes escaped

    (r'1\n2|3\n\n4',    ['1\n2','3\n\n4']),     # \n escaped
    (r'm\\n',           ['m\\n']),              # escape \, not \n
    (r'\n1|2\n',        ['\n1','2\n']),         # start with \n, end with \n

    (r'1\r2|3\r\n4',    ['1\r2','3\r\n4']),     # \r escaped
    ]

    def test_encode_and_decode(self):
        # Test a round trip of decode and encode
        for line, result in self.DATA:
            self.assertEqual(store.decode_dsv(line), result)
            self.assertEqual(store.encode_dsv(result), line)

    def test_row_object(self):
        headers = store.parse_header(1, 'col1|col2')
        fields = store.decode_dsv('a|b')
        row = store.RowObject(headers, fields)
        self.assertEqual(row.col1, 'a')
        self.assertEqual(row.col2, 'b')
        self.assertRaises(AttributeError, row.__getattr__, 'col3')

    def test_row_object_compatibility(self):
        expected_col = ['col2','col3']
        headers = store.parse_header(1, 'col1|col2', expected_col)
        fields = store.decode_dsv('a|b')
        row = store.RowObject(headers, fields)
        self.assertEqual(row.col1, 'a')     # not in expected, but will work
        self.assertEqual(row.col2, 'b')
        self.assertEqual(row.col3, '')      # expected col not in data header, gets ''
        self.assertRaises(AttributeError, row.__getattr__, 'col4')



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


    def test_getWriter(self):
        # test _getWriter() prepare fp for non-exist or 0 size file.
        stor = store.Store()
        self.assert_('test' in stor.pathname)

        # ------------------------------------------------------------------------
        # make sure weblib file does not exist
        try:
            os.remove(stor.pathname)
        except OSError:
            pass
        self.assert_(not os.path.exists(stor.pathname))

        # test _getWriter() probably write headers for non-exist file
        out = stor._getWriter()
        self.assert_(os.path.exists(stor.pathname))
        self.assert_(os.path.getsize(stor.pathname) > 0)

        # test current position is > 0
        # write some dummy chars to initialize tell()?
        out.write('#\n')
        self.assert_(out.tell() > 2)

        stor.reset()

        # ------------------------------------------------------------------------
        # make it a 0 size file
        fp = file(stor.pathname,'wb')
        fp.close()
        self.assert_(os.path.getsize(stor.pathname) == 0)

        # test _getWriter() probably write headers for 0 size file
        out = stor._getWriter()
        self.assert_(os.path.exists(stor.pathname))
        self.assert_(os.path.getsize(stor.pathname) > 0)

        # test current position is > 0
        # write some dummy chars to initialize tell()?
        out.write('#\n')
        self.assert_(out.tell() > 2)

        stor.reset()

        # ------------------------------------------------------------------------
        # clean up
        os.remove(stor.pathname)


    def test_upgrade(self):
        stor = store.Store()
        self.assert_('test' in stor.pathname)

        # ------------------------------------------------------------------------
        # build a barebone old version test file
        test_data = """weblib-version: 0.01\r
encoding: utf-8\r
\r
20060112T063529Z!U url.1|1|item1|description1
"""
        self.assert_(stor.VERSION != '0.01')
        self.assert_(stor.VERSION not in test_data)
        fp = file(stor.pathname,'wb')
        fp.write(test_data)
        fp.close()

        stor.load()
        wlib = stor.wlib
        self.assertEqual(wlib.version, '0.01')
        self.assertEqual(len(wlib.webpages), 1)
        self.assertEqual(wlib.webpages.getById(1).name, 'item1')

        # this should trigger store to upgrade the file
        stor.writeNameValue('a_name','a_value')

        # test the upgraded file
        fp = file(stor.pathname,'rb')
        newData = fp.read()
        fp.close()

        self.assert_('0.01' not in newData)
        self.assert_(stor.VERSION in newData)

        # clean up
        stor.reset()
#        os.remove(stor.pathname)


    def test_colum_compatibility(self):
        stor = store.Store()
        self.assert_('test' in stor.pathname)

        # ------------------------------------------------------------------------
        # Note the column is assignment is different from what defined in Store
        # column 'anme' and 'description' comes in different order
        # column 'wacky' is not fined in Store
        # column 'url' is missing
        test_data = """weblib-version: 0.07\r
encoding: utf-8\r
url-columns: id|version|wacky|description|name
\r
20060112T063529Z!U url.1|1|xxx|description1|item1
"""
        fp = file(stor.pathname,'wb')
        fp.write(test_data)
        fp.close()

        stor.load()
        wlib = stor.wlib
        self.assertEqual(wlib.version, '0.07')
        self.assertEqual(len(wlib.webpages), 1)

        # test item is loaded ok
        item = wlib.webpages.getById(1)
        self.assertEqual(item.name, 'item1')
        self.assertEqual(item.description, 'description1')
        # column 'url' not exist and assumed to be ''
        self.assertEqual(item.url, '')
        # column 'wacky' is just ignored


    def test_dsv_encode_error(self):
        stor = store.Store()
        self.assert_('test' in stor.pathname)

        # ------------------------------------------------------------------------
        # Note url.1's name is not properly encoded. Make sure it is dropped
        # without affecting the reading of the rest of record.
        test_data = """weblib-version: 0.07\r
encoding: utf-8\r
\r
20060112T063529Z!U url.1|1|item\\|description1
20060112T063529Z!U url.2|1|item\\\\|description2
"""
        fp = file(stor.pathname,'wb')
        fp.write(test_data)
        fp.close()

        stor.load()
        wlib = stor.wlib

        self.assertEqual(len(wlib.webpages), 1)

        # url.1 is dropped
        self.assert_(not wlib.webpages.getById(1))

        # url.2 is ok
        item = wlib.webpages.getById(2)
        self.assertEqual(item.name, 'item\\')


    def test_write_name_value(self):
        wlib = self.store.wlib
        self._make_test_data()

        # before
        self.assertEqual(wlib.category.getDescription(), '')
        nt, nw = len(wlib.tags), len(wlib.webpages)

        # write
        self.store.writeNameValue('category_description', 'xyz')
        self.store.writeNameValue('a_name', 'a_value')  # would be ignored, just try to run it

        # after
        self.assertEqual(wlib.category.getDescription(), 'xyz')
        self._assert_weblib_size(nt, nw)

        # TODO: versioning of name value?


    def test_write_tag_new(self):
        wlib = self.store.wlib
        self._make_test_data()
        timestamp0 = store._getTimeStamp()
        self.assert_(timestamp0)

        # ------------------------------------------------------------------------
        # before
        nt, nw = len(wlib.tags), len(wlib.webpages)
        self.assert_('Tag1' not in self.buf.getvalue())

        # write
        tag = weblib.Tag(name='Tag1')
        self.assertEqual(tag.id, -1)
        newTag = self.store.writeTag(tag)

        # after
        self._assert_weblib_size(nt+1, nw)
        self.assert_('Tag1' in self.buf.getvalue())

        self.assert_(newTag.id >= 0)
        t = wlib.tags.getByName('tag1')
        self.assert_(t)
        self.assertEqual(t.id, newTag.id)
        self.assert_(t.timestamp >= timestamp0)
        self.assert_(t.version >= 1)

        # ------------------------------------------------------------------------
        # before
        self.assert_(not wlib.tags.getById(10))

        # write webpage with new id assigned
        tag = weblib.Tag(id=10, name='Tag10')
        newTag = self.store.writeTag(tag)

        # verify
        self._assert_weblib_size(nt+2, nw)
        t = wlib.tags.getById(10)
        self.assertEqual(t.name, 'Tag10')
        self.assert_(t.timestamp >= timestamp0)
        self.assert_(t.version >= 1)


    def test_write_tag_existing(self):
        wlib = self.store.wlib
        self._make_test_data()

        # before
        nt, nw = len(wlib.tags), len(wlib.webpages)
        self.assert_('new tag1' not in self.buf.getvalue())
        t = wlib.tags.getByName('def_tag1')
        self.assert_(t)
        timestamp0 = t.timestamp
        version0 = t.version

        # write (i.e. update)
        t1 = t.__copy__()
        t1.name = 'new tag1'
        self.store.writeTag(t1)

        # after
        self._assert_weblib_size(nt, nw)
        self.assert_('new tag1' in self.buf.getvalue())
        self.assert_(not wlib.tags.getByName('def_tag1'))
        t = wlib.tags.getByName('new tag1')
        self.assert_(t)
        self.assert_(t.timestamp >= timestamp0)
        self.assert_(t.version > version0)


    def test_write_tag_duplicated(self):
        wlib = self.store.wlib
        self._make_test_data()

        # before
        nt, nw = len(wlib.tags), len(wlib.webpages)
        self.assert_(not wlib.tags.getByName('TESTTAG'))
        self.assert_(not wlib.tags.getByName('TESTTAG[1]'))
        self.assert_(not wlib.tags.getByName('TESTTAG[2]'))

        # write 1st TESTTAG
        tag = weblib.Tag(name='TESTTAG')
        newTag = self.store.writeTag(tag)
        self._assert_weblib_size(nt+1, nw)
        self.assert_(wlib.tags.getByName('TESTTAG'))

        # write 2nd TESTTAG
        tag = weblib.Tag(name='TESTTAG')
        newTag = self.store.writeTag(tag)
        self._assert_weblib_size(nt+2, nw)
        self.assert_(wlib.tags.getByName('TESTTAG[1]'))

        # write 3rd TESTTAG
        tag = weblib.Tag(name='TESTTAG')
        newTag = self.store.writeTag(tag)
        self._assert_weblib_size(nt+3, nw)
        self.assert_(wlib.tags.getByName('TESTTAG[2]'))


    def test_write_webpage_new(self):
        wlib = self.store.wlib
        self._make_test_data()
        timestamp0 = store._getTimeStamp()
        self.assert_(timestamp0)

        # ------------------------------------------------------------------------
        # before
        nt, nw = len(wlib.tags), len(wlib.webpages)
        self.assert_('Page1' not in self.buf.getvalue())

        # write
        page = weblib.WebPage(name='Page1')
        self.assertEqual(page.id, -1)
        newPage = self.store.writeWebPage(page)

        # after
        self._assert_weblib_size(nt, nw+1)
        self.assert_('Page1' in self.buf.getvalue())
        self.assert_(newPage.id >= 0)
        page = wlib.webpages.getById(newPage.id)
        self.assert_(page)
        self.assert_(page.timestamp >= timestamp0)
        self.assert_(page.version >= 1)

        # ------------------------------------------------------------------------
        # before
        self.assert_(not wlib.webpages.getById(10))

        # write webpage with new id assigned
        page = weblib.WebPage(id=10, name='Page10')
        newPage = self.store.writeWebPage(page)

        # verify
        self._assert_weblib_size(nt, nw+2)
        page = wlib.webpages.getById(10)
        self.assertEqual(page.name, 'Page10')
        self.assert_(page.timestamp >= timestamp0)
        self.assert_(page.version >= 1)


    def test_write_webpage_existing(self):
        wlib = self.store.wlib
        self._make_test_data()

        # before
        nt, nw = len(wlib.tags), len(wlib.webpages)
        self.assert_('new page1' not in self.buf.getvalue())
        page = wlib.webpages.getById(1)
        self.assertEqual(page.name, 'def_page1')
        timestamp0 = page.timestamp
        version0 = page.version

        # write
        p1 = page.__copy__()
        p1.name = 'new page1'
        self.store.writeWebPage(p1)

        # after
        self._assert_weblib_size(nt, nw)
        self.assert_('new page1' in self.buf.getvalue())
        page = wlib.webpages.getById(1)
        self.assertEqual(page.name, 'new page1')
        self.assert_(page.timestamp >= timestamp0)
        self.assert_(page.version > version0)


    def test_remove_tag(self):
        wlib = self.store.wlib
        self._make_test_data()

        # before
        nt, nw = len(wlib.tags), len(wlib.webpages)
        self.assert_('!X tag.1' not in self.buf.getvalue())

        # remove
        self.store.removeItem(wlib.tags.getById(1))

        # after
        self._assert_weblib_size(nt-1, nw)
        self.assertEqual(wlib.tags.getById(1), None)
        # got the delete line
        self.assert_('!X tag.1' in self.buf.getvalue())


    def test_remove_webpage(self):
        wlib = self.store.wlib
        self._make_test_data()

        # before
        nt, nw = len(wlib.tags), len(wlib.webpages)
        self.assert_('!X url.1' not in self.buf.getvalue())

        # remove
        self.store.removeItem(wlib.webpages.getById(1))

        # after
        self._assert_weblib_size(nt, nw-1)
        self.assertEqual(wlib.webpages.getById(1), None)
        # got the delete line
        self.assert_('!X url.1' in self.buf.getvalue())


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
        self.assert_(item)
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
                lineno, line0 = iter0.next()        # skip date header
            line1 = output.next()
            while line1.startswith('date:'):
                line1 = output.next()               # skip date header

            # compare it line by line so error is easier to spot
            line0 = line0.rstrip()
            line1 = line1.rstrip()
            timestamp_idx = len('20010101T010203Z')
            self.assertEqual(line0[timestamp_idx:], line1[timestamp_idx:], 'line %s\nfile0: %s\nfile1: %s' % (lineno+1,
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
        self.assertEqual(wlib.category.getDescription(), 'Kremlin')
        self.assert_(wlib.tags.getByName('tag1'))
        self.assert_(wlib.tags.getByName('tag2'))
        self.assert_(not wlib.tags.getByName('English'))
        self.assert_(not wlib.webpages.getById(2))


    def test_change_n_save(self):
        # change wlib and generates change records
        # reload the changed data file to ensure changes are playback correctly
        # similarly test the saved snapshot data file
        self._load_TESTFILE()
        self._assert_weblib_size(6, 5)
        wlib = self.store.wlib

        # change data
        self.store.writeNameValue('category_description', 'Kremlin')

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
        self.assert_( changed_data.startswith(self.TESTTEXT))

        # reload changed data file
        old_weblib = self.store.wlib
        self.store.load('*changed*buffer*', StringIO.StringIO(changed_data))
        self.assert_(self.store.wlib is not old_weblib)  # a new wlib is really loaded :)
        self._check_changed()

        # save data file snapshot
        buf = StringIO.StringIO()
        self.store.save('*snapshot*buffer*', buf)
        snapshot_data = buf.getvalue()
        # unlike changed data snapshot save records without change records
        self.assert_( not snapshot_data.startswith(self.TESTTEXT))

        # load snapshot and verify
        old_weblib = self.store.wlib
        self.store.load('*snapshot*buffer*', StringIO.StringIO(snapshot_data))
        self.assert_(self.store.wlib is not old_weblib)  # a new wlib is really loaded :)
        self._check_changed()


    def test_timestamp(self):
        ts = store._getTimeStamp()
        self.assertEqual(len(ts), len('12340618T123456Z'))


if __name__ == '__main__':
    unittest.main()
