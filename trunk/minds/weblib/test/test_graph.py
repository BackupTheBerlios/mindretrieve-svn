import unittest

from minds.weblib import graph

Node = graph.Node

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
            C1
    """

    DEFORMED = """
C1
  C11
  C12
     C121
    C122x
 C13x
  C131
"""

    def test0(self):
        self.assertEqual(graph.parse_text_tree(''), Node(''))
        self.assertEqual(graph.parse_text_tree('\n'), Node(''))


    def test_simple(self):
        tree = graph.parse_text_tree(self.DATA)
        expected = Node('', [
        Node('C1', [
            Node('C11',[]),
            Node('C12',[
                Node('C121',[]),
                Node('C122',[]),
            ]),
            Node('C13',[]),
        ]),
        Node('C2', [
            Node('C21', [
                Node('C211',[]),
            ]),
        ]),
        Node('C3', [
            Node('C31',[]),
            Node('C1',[]),
        ]),
        ])
        self.assertEqual(tree, expected)


    def test_deformed(self):
        tree = graph.parse_text_tree(self.DEFORMED)
        expected = Node('', [
        Node('C1', [
            Node('C11',[]),
            Node('C12',[
                Node('C121',[]),
                Node('C122x',[]),   # child of C12, although it has smaller indent than sibling C121
            ]),
            Node('C13x',[           # child of C1, although it has smaller indent than sibling C12
                Node('C131',[]),    # C131 is child of C13x, although it has same indent as uncle C12
            ]),
        ]),
        ])
        self.assertEqual(tree, expected)

        # it looks odd, but they are siblings
        self.assertEqual(graph.parse_text_tree("""
    C1
C2""" ), Node('', [Node('C1',[]), Node('C2',[])]))


    def test_dfs(self):
        tree = graph.parse_text_tree(self.DATA)
        result = [(node.data, len(p)) for node, p in tree.dfs()]
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
            ('C1',2),
        ]
        self.assertEqual(result, expected)


    def test_bfs(self):
        tree = graph.parse_text_tree(self.DATA)
        result = [(node.data,level) for node,level in tree.bfs()]
        expected = [
            ('',0),
            ('C1',1),
            ('C2',1),
            ('C3',1),
            ('C11',2),
            ('C12',2),
            ('C13',2),
            ('C21',2),
            ('C31',2),
            ('C1',2),
            ('C121',3),
            ('C122',3),
            ('C211',3),
        ]
        self.assertEqual(result, expected)


    def test_rename(self):
        # blank tests
        self._check_rename('', '', '',[])
        self._check_rename('', 'C1', 'X1',[])
        self._check_rename('\n', 'C1', 'X1',[])

        self._check_rename(self.DATA, 'C1', 'X1',[1,12])    # 2 renamed
        self._check_rename(self.DATA, 'c1', 'X1',[1,12])    # lower case also OK
        self._check_rename(self.DATA, 'c12', 'abc',[3])     # 1 renamed
        self._check_rename(self.DATA, 'C211', 'def',[9])    # 1 renamed

        self._check_rename(self.DATA, 'XXX', 'YYY',[])      # non-exist tag


    def _check_rename(self, DATA, tag0, tag1, expected_diff):
        edited, count = graph.edit_text_tree_rename(DATA, tag0, tag1)

        # this is simple test, assume not 2 word tags
        data_words = DATA.lower().split()
        edited_words = edited.lower().split()
        ltag0 = tag0.lower()
        ltag1 = tag1.lower()

        self.assertEqual(count, len(expected_diff))
        self.assertTrue(ltag0 not in edited_words)
        if ltag0 in data_words:
            self.assertTrue(ltag1 in edited_words)
        self.assertEqual(len(DATA.splitlines()), len(edited.splitlines()))

        # check line diff
        diff = []
        for i,line1,line2 in zip(xrange(9999), DATA.splitlines(), edited.splitlines()):
            if line1 != line2:
                diff.append(i)
        self.assertEqual(expected_diff, diff)


    def test_delete(self):
        # blank tests
        self.assertEqual(graph.edit_text_tree_delete('', ''), ('',0))
        self.assertEqual(graph.edit_text_tree_delete('\n', ''), ('\n',0))
        self.assertEqual(graph.edit_text_tree_delete('', 'xx'), ('',0))

        # tag not found is OK
        self.assertEqual(graph.edit_text_tree_delete(self.DEFORMED, 'XX'), (self.DEFORMED,0))

        # this one cause realignment of deformed children
        # also it invokes the final _trim_children_and_output()
        self.assertEqual(graph.edit_text_tree_delete(self.DEFORMED, 'C1'), ("""
C11
C12
   C121
  C122x
C13x
 C131
""",1))

        # this is a leaf node and affects no child
        self.assertEqual(graph.edit_text_tree_delete(self.DEFORMED, 'C11'), ("""
C1
  C12
     C121
    C122x
 C13x
  C131
""",1))
        self.assertEqual(graph.edit_text_tree_delete(self.DEFORMED, 'C12'), ("""
C1
  C11
  C121
  C122x
 C13x
  C131
""",1))
        self.assertEqual(graph.edit_text_tree_delete(self.DEFORMED, 'C131'), ("""
C1
  C11
  C12
     C121
    C122x
 C13x
""",1))

        # delete multiple occurance, alos match case insensitively
        self.assertEqual(graph.edit_text_tree_delete("""
c1
    a
c1
    b
C
    c1
        d
e
    C1
""", 'C1'), ("""
a
b
C
    d
e
""",4))



class TestUtils(unittest.TestCase):

    def test_find_branches(self):
        DATA = """
        C1
            C11
            XYZ
                C121
                C122
            C13
        XYZ
            C21
                C211
        C3
            XYZ
            C1

        """
        tree = graph.parse_text_tree(DATA)

        # find non-exist branches
        # current implementation think it is better to return ['NOT EXIST'] than []
        branches = graph.find_branches(tree, 'NOT EXIST')
        children = [node.data for node,_ in branches.dfs()]
        self.assertEqual(children, ['NOT EXIST'])

        # find XYZ and its children
        branches = graph.find_branches(tree, 'XYZ')
        children = [node.data for node,_ in branches.dfs()]
        self.assertEqual(children, [
            'XYZ',
            'C121',
            'C122',
            'C21',
            'C211',
        ])



if __name__ =='__main__':
    unittest.main()
