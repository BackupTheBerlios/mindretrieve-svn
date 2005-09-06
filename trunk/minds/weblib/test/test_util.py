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


    def test_remove(self):
        super(TestIdNameList,self).test_remove()


#-----------------------------------------------------------------------
# Indented text parsing        

class TestIndentedTextParsing(unittest.TestCase):
    
    DATA = """
        C1
            C11
            C12
                C121
                C122
            C13
        C2
            C21
                C211
        C3
            C31                   
    """

    def test0(self):
        tree = util.parse_indent_text('')
        self.assertEqual(tree, ('',[]))
        
        tree = util.parse_indent_text('\n')
        self.assertEqual(tree, ('',[]))

    def test_simple(self):
        tree = util.parse_indent_text(self.DATA)
        expected = ('', [
        ('C1', [
            ('C11',[]),
            ('C12',[
                ('C121',[]),
                ('C122',[]),
            ]),
            ('C13',[]),
        ]),
        ('C2', [
            ('C21', [
                ('C211',[]),
            ]),
        ]),
        ('C3', [
            ('C31',[]),
        ]),
        ])
        self.assertEqual(tree, expected)


    def test_dfs(self):
        tree = util.parse_indent_text(self.DATA)
        result = [(node[0], level) for node,level in util.dfs(tree)]
        expected = [
            ('',0),
            ('C1',1),
            ('C11',2),
            ('C12',2),
            ('C121',3),
            ('C122',3),
            ('C13',2),
            ('C2',1),
            ('C21',2),
            ('C211',3),
            ('C3',1),
            ('C31',2),
        ]
        self.assertEqual(result, expected)
        
        
if __name__ =='__main__':
    unittest.main()
        