import unittest

from minds.weblib import util


#-----------------------------------------------------------------------
# Id keyed list

class TestItem(object):

    # for generating unique names
    nameId = 1

    def __init__(self,id=-1,name=None):
        self.id = id
        if not name:
            name = 'item%s' % TestItem.nameId
            TestItem.nameId += 1
        self.name = name

    def __str__(self):
        return self.name


class TestIdList(unittest.TestCase):

    def setUp(self):
        TestItem.nameId = 1
        self.lst = util.IdList()

    def test0(self):
        self.assertEqual(len(self.lst), 0)
        for i in self.lst:
            self.fail('expect empty')

    def test_first(self):
        # make sure id start from a positive number
        # id of 0 would cause a lot of trouble
        first_item = TestItem()
        self.lst.append(first_item)
        self.assertTrue(first_item.id > 0)

    def test3(self):
        item1 = TestItem()
        item2 = TestItem()
        item3 = TestItem()
        self.lst.append(item1)
        self.lst.append(item2)
        self.lst.append(item3)

        self.assertEqual(len(self.lst), 3)
        self.assertEqual(self.lst.getById(0), None)
        self.assertEqual(self.lst.getById(1), item1)
        self.assertEqual(self.lst.getById(2), item2)
        self.assertEqual(self.lst.getById(3), item3)
        self.assertEqual(self.lst.getById(4), None)
        self.assertEqual(self.lst._lastId, 3)

        # test __iter__
        enum = [(item.id, item) for item in self.lst]
        expected = zip(range(1,4), [item1, item2, item3])
        self.assertEqual(enum, expected)


    def test_with_id(self):
        item1 = TestItem(11)
        item2 = TestItem(12)
        item3 = TestItem(13)
        self.lst.append(item1)
        self.lst.append(item2)
        self.lst.append(item3)

        self.assertEqual(len(self.lst), 3)
        self.assertEqual(self.lst.getById(0), None)
        self.assertEqual(self.lst.getById(1), None)
        self.assertEqual(self.lst.getById(11), item1)
        self.assertEqual(self.lst.getById(12), item2)
        self.assertEqual(self.lst.getById(13), item3)
        self.assertEqual(self.lst._lastId, 13)

        # test __iter__
        enum = [(item.id, item) for item in self.lst]
        expected = zip(range(11,14), [item1, item2, item3])
        self.assertEqual(enum, expected)


    def test_duplicates(self):
        item1 = TestItem(7)
        item2 = TestItem(7)

        # OK to append item1
        self.lst.append(item1)
        self.assertEqual(len(self.lst), 1)

        # reject duplicated item2
        self.assertRaises(KeyError, self.lst.append, item2)
        self.assertEqual(len(self.lst), 1)

    def test_remove(self):
        item1 = TestItem()
        item2 = TestItem()
        item3 = TestItem()
        self.lst.append(item1)
        self.lst.append(item2)
        self.lst.append(item3)

        # originally has 3 items
        self.assertEqual(len(self.lst), 3)
        self.assertEqual(self.lst.getById(1), item1)

        self.lst.remove(item1)

        # only 2 items remain
        self.assertEqual(len(self.lst), 2)
        self.assertEqual(self.lst.getById(1), None)
        enum = [(item.id, item) for item in self.lst]
        expected = zip(range(2,4), [item2, item3])
        self.assertEqual(enum, expected)

        # can't delete this again
        self.assertRaises(KeyError, self.lst.remove, item1)
        self.assertEqual(len(self.lst), 2)


    def test_failfast(self):
        item1 = TestItem()
        item2 = TestItem()
        item3 = TestItem()
        self.lst.append(item1)
        self.lst.append(item2)
        self.lst.append(item3)

        # fine for simple iteration
        for item in self.lst:
            pass

        # fail fast if append during iteration
        try:
            for item in self.lst:
                if len(self.lst) < 10:
                    self.lst.append(TestItem())
        except RuntimeError:
            # fail after first iteration
            self.assertEqual(item, item1)
        else:
            self.fail('Fail fast expected.')

        # fail fast if remove during iteration
        try:
            for item in self.lst:
                self.lst.remove(item)
        except RuntimeError:
            # fail after first iteration
            self.assertEqual(item, item1)
        else:
            self.fail('Fail fast expected.')



class TestIdNameList(TestIdList):

    def setUp(self):
        TestItem.nameId = 1
        self.lst = util.IdNameList()


    def test3(self):
        super(TestIdNameList,self).test3()
        self.assertEqual(self.lst.getByName(''), None)
        self.assertEqual(self.lst.getByName('item1').id, 1)
        self.assertEqual(self.lst.getByName('item2').id, 2)
        self.assertEqual(self.lst.getByName('item3').id, 3)
        self.assertEqual(self.lst.getByName('ITEM3').id, 3) # mix case should match
        self.assertEqual(self.lst.getByName('not exist'), None)


    def test_blank(self):
        blank_item = TestItem(100, '')
        # erase generated name
        blank_item.name = ''
        self.assertRaises(KeyError, self.lst.append, blank_item)


    def test_duplicates(self):
        super(TestIdNameList,self).test_duplicates()

        # flush the list
        self.lst = util.IdNameList()

        item1 = TestItem(1, 'same')
        item2 = TestItem(2, 'same')

        # OK to append item1
        self.lst.append(item1)
        self.assertEqual(len(self.lst), 1)

        # reject duplicated item2
        self.assertRaises(KeyError, self.lst.append, item2)
        self.assertEqual(len(self.lst), 1)


    def test_rename(self):
        # insert 'item1'
        item1 = TestItem()
        self.lst.append(item1)

        # rename item1
        self.lst.rename(item1, 'newName')

        gbn = self.lst.getByName
        self.assertEqual(gbn('item1'), None)                # old name is gone
        self.assertEqual(gbn('newName'), item1)             # new name refers to former item1
        self.assertEqual(gbn('NEWNAME'), item1)             # mix case should match
        self.assertEqual(gbn('newName').name, 'newName')    # name has changed


    def test_rename_capitalization(self):
        # insert 'item1'
        item1 = TestItem()
        self.lst.append(item1)

        # rename item1 to ITEM1
        self.lst.rename(item1, 'ITEM1')

        gbn = self.lst.getByName
        self.assertEqual(gbn('item1'), item1)           # refer to item1
        self.assertEqual(gbn('ITEM1'), item1)           # refer to item1
        self.assertEqual(gbn('ITEM1').name, 'ITEM1')    # name has changed

        # change it back to lower case (dictionary format)
        self.lst.rename(item1, 'item1')

        self.assertEqual(gbn('item1'), item1)           # refer to item1
        self.assertEqual(gbn('ITEM1'), item1)           # refer to item1
        self.assertEqual(gbn('item1').name, 'item1')    # name has changed


    def test_invalid_rename(self):
        # insert 'item1' and 'item2'
        item1 = TestItem()
        item2 = TestItem()
        self.lst.append(item1)
        self.lst.append(item2)
        self.assertTrue(self.lst.getByName('item1'))
        self.assertTrue(self.lst.getByName('item2'))

        # rename item1 to item2
        item = self.lst.getByName('item1')
        self.assertRaises(KeyError, self.lst.rename, item, 'item2')

        # rename item1 to blank
        self.assertRaises(KeyError, self.lst.rename, item, '')


    def test_remove(self):
        super(TestIdNameList,self).test_remove()


if __name__ =='__main__':
    unittest.main()
