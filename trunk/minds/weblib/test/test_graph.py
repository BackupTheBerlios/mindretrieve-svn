import unittest

from minds.weblib import util


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
        tree = graph.build_indented_text_DAG('')
        self.assertEqual(tree, ('',[]))

        tree = graph.build_indented_text_DAG('\n')
        self.assertEqual(tree, ('',[]))

    def test_simple(self):
        tree = graph.build_indented_text_DAG(self.DATA)
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
        tree = graph.build_indented_text_DAG(self.DATA)
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
