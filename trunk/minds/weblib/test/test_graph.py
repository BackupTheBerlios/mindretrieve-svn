import unittest

from minds.weblib import graph


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
        edited = graph.edit_text_tree_rename(DATA, tag0, tag1)

        # this is simple test, assume not 2 word tags
        edited_words = edited.lower().split()
        data_words = DATA.lower().split()
        ltag0 = tag0.lower()
        ltag1 = tag1.lower()

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


    def test0(self):
        tree = graph.parse_text_tree('')
        self.assertEqual(tree, ['',[]])

        tree = graph.parse_text_tree('\n')
        self.assertEqual(tree, ['',[]])


    def test_simple(self):
        tree = graph.parse_text_tree(self.DATA)
        expected = ['', [
        ['C1', [
            ['C11',[]],
            ['C12',[
                ['C121',[]],
                ['C122',[]],
            ]],
            ['C13',[]],
        ]],
        ['C2', [
            ['C21', [
                ['C211',[]],
            ]],
        ]],
        ['C3', [
            ['C31',[]],
            ['C1',[]],
        ]],
        ]]
        self.assertEqual(tree, expected)


    def test_deformed(self):
        tree = graph.parse_text_tree(self.DEFORMED)
        expected = ['', [
        ['C1', [
            ['C11',[]],
            ['C12',[
                ['C121',[]],
                ['C122x',[]],   # child of C12, although it has smaller indent than sibling C121
            ]],
            ['C13x',[           # child of C1, although it has smaller indent than sibling C12
                ['C131',[]],    # C131 is child of C13x, although it has same indent as uncle C12
            ]],
        ]],
        ]]
        self.assertEqual(tree, expected)


    def test_dfs(self):
        tree = graph.parse_text_tree(self.DATA)
        result = list(graph.dfs(tree))
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


if __name__ =='__main__':
    unittest.main()
