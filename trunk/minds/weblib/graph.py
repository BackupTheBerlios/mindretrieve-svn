""" Graph utilities

The graphs used here are directed acyclic graphs. Usually there an arbitrary
root node added at the starting point of traversal.
"""

import sys


#-----------------------------------------------------------------------

class CycleError(Exception): pass

class TooManyLevelsError(Exception): pass

class Node(object):

    # heuristic for disaster control
    MAX_DEPTH = 20

    def __init__(self, data, children=None):
        self.data = data
        if children:
            self.children = children
        else:
            self.children = []  # default is a new list


    def dfs(self, path=None):
        """ Walk in DFS order, yield (node, path to node) """

        if path is None:
            path = []   # create a new initial path list
        if len(path) > self.MAX_DEPTH:
            raise TooManyLevelsError('Tree has too many level: %s(%s)' % (unicode(self), self.MAX_DEPTH))

        yield self, path
        path.append(self)
        for child in self.children:
            for x in child.dfs(path): yield x
        path.pop()


    def dfs_ctx(self, visit_record=None):
        """
        Yield visit_record of this node and all decendant nodes in DFS order.
        visit_record is a list of [node, idx, path, user field].

        Note: path get modified between yields.
        Make a copy if a permanent record is needed.
        """

        if not visit_record:
            visit_record = [self, 0, [], None]
        path = visit_record[2]

        # safety valve
        if len(path) > self.MAX_DEPTH:
            raise TooManyLevelsError('Tree has too many level: %s(%s)' % (unicode(self), self.MAX_DEPTH))

        yield visit_record

        # we may come back with a user field
        # propagate this to decendants
        user_field = visit_record[3]

        path.append(visit_record)

        for idx, child in enumerate(self.children):
            visit_child = [child, idx, path, user_field]
            for x in child.dfs_ctx(visit_child): yield x
        path.pop()


    def bfs(self):
        """ Walk in BFS order, yield node, level """
        fifo = [(self,0)]
        while fifo:
            node, level = fifo.pop(0)
            if level > self.MAX_DEPTH:
                raise TooManyLevelsError('Tree has too many level: %s(%s)' % (unicode(node), self.MAX_DEPTH))
            yield node, level
            next_level = [level+1] * len(node.children)
            fifo.extend(zip(node.children, next_level))
        # TODO: disaster control in case of loop


    def dump(self, out=sys.stdout):
        for node, path in self.dfs():
            if node:
                out.write('..'*len(path)+ unicode(node))
                out.write('\n')


    def __cmp__(self, other):
        if not isinstance(other, Node):
            return -1
        if self.data == other.data:
            return cmp(self.children, other.children)
        else:
            return cmp(self.data, other.data)


    def __repr__(self):
        return u'%s:%s' % (unicode(self.data), len(self.children))


    def __str__(self):
        return unicode(self.data)



#-----------------------------------------------------------------------
# Indented text parsing

def _split_indent(s):
    """
    Split a string into (indent, data).  e.g.

    >>> _split_indent("  hello")
    (2, 'hello')
    """
    data = s.lstrip(' ')
    indent = len(s) - len(data)
    return indent, data


def _parse_lines(data):
    """ generates lines from data """
    for line in data.splitlines():
        line = line.rstrip()
        if not line:
            continue
        yield line


def parse_text_tree(data):
    """
    Parse input of indented text into a graph of nodes.
    Return the root node.
    """
    root_node = Node('')

    cur_node = root_node
    cur_indent = -1

    # stack of (indent, node) starts with the root node
    stack = [(cur_indent,cur_node)]

    # Note these conditions should always hold
    # - indent in the stack would be strictly increasing
    # - the root node will never be popped
    # - cur_indent, cur_node == stack[-1]

    for line in _parse_lines(data):
        indent, name = _split_indent(line)
        node = Node(name)

        # Look for parent with smaller indent (i.e. cur_indent < indent)
        # case 1: cur_indent < indent, last line is the parent, no popping necessary.
        # case 2: cur_indent == indent, this line is a sibling of last line. One pop should find the parent
        # case 3: cur_indent > indent, one or more pop to find the parent.
        while cur_indent >= indent:
            # note: -1 < 0 <= indent <= cur_indent
            # i.e. there is at least 2 items in the stack
            stack.pop()
            cur_indent, cur_node = stack[-1]

        # note: You may find this line has a smaller ident than its
        # older sibling. The tree is deformed but it is reasonable
        # to accept this defect.
        #
        # Example of a deformed tree:
        #   C1
        #   ....C11
        #   ..C12     <-- Child of C1, it should really align with C11
        #   ....C121  <-- this will become child of C12, not sibling of C11

        # append to parent
        cur_node.children.append(node)

        # the new cur_node
        cur_indent,cur_node = indent,node
        stack.append((cur_indent,cur_node))

    return root_node


#def parse_text_tree_old(data):
#    """
#    Parse input of indented text into a graph of nodes.
#    Return the root node.
#
#    A node is a 2-tuple of [name, list of children)]
#    It is represented by list so that the elements can be updated.
#    """
#    root_node = ['',[]]
##    nodes = {'': root_node}
#
#    cur_node = root_node
#    cur_indent = -1
#
#    # stack of (indent, node) starts with the root node
#    stack = [(cur_indent,cur_node)]
#
#    # Note these conditions should always hold
#    # - indent in the stack would be strictly increasing
#    # - the root node will never be popped
#    # - cur_indent, cur_node == stack[-1]
#
#    for line in _parse_lines(data):
#        indent, name = _split_indent(line)
#        node = [name,[]]
##        name = name.lower()
##        node = nodes.setdefault(name,[name,[]])
#
#        # Look for parent with smaller indent (i.e. cur_indent < indent)
#        # case 1: cur_indent < indent, last line is the parent, no popping necessary.
#        # case 2: cur_indent == indent, this line is a sibling of last line. One pop should find the parent
#        # case 3: cur_indent > indent, one or more pop to find the parent.
#        while cur_indent >= indent:
#            # note: -1 < 0 <= indent <= cur_indent
#            # i.e. there is at least 2 items in the stack
#            stack.pop()
#            cur_indent, cur_node = stack[-1]
#
#        # note: You may find this line has a smaller ident than its
#        # older sibling. The tree is deformed but it is reasonable
#        # to accept this defect.
#        #
#        # Example of a deformed tree:
#        #   C1
#        #   ....C11
#        #   ..C12     <-- Child of C1, it should really align with C11
#        #   ....C121  <-- this will become child of C12, not sibling of C11
#
#        # append to parent
#        cur_node[1].append(node)
#
#        # the new cur_node
#        cur_indent,cur_node = indent,node
#        stack.append((cur_indent,cur_node))
#
#    return root_node


def edit_text_tree_rename(data, tag0, tag1):
    """
    tag0 has renamed to tag1.
    Apply the same changed to text tree, preserve
    white space and capitalization if possible.

    @return new text, number of tag0 changed
    """
    tag0 = tag0.lower()
    output = []
    count = 0
    for line in data.splitlines(True):
        if line.strip().lower() == tag0:
            line = line.lower().replace(tag0,tag1)
            count += 1
        output.append(line)
    return ''.join(output), count


def edit_text_tree_delete(data, tag0):
    """
    tag0 has been deleted.
    Apply the same changed to text tree, preserve
    white space and capitalization if possible.
    Realign children lines if necessary.

    @return new text, number of tag0 changed
    """
    tag0 = tag0.lower()
    output = []
    count = 0

    # indent of the row to be trimmed. Also a flag for the trimming
    # state. None mean we are not in trimming state.
    trim_indent = None

    for line in data.splitlines(True):
        if line.isspace():
            if trim_indent == None:
                output.append(line)
            else:
                children.append((None,line))
            continue

        indent, name = _split_indent(line)

        # trim_indent determine if we are in trimming state
        if trim_indent != None:
            if indent <= trim_indent:
                # leave trim mode
                _trim_children_and_output(trim_indent, children, output)
                trim_indent = None
                children = [] # tidy up
            else:
                # TODO: What if this line also contain tag0!!!
                # This is an obvious cycle, shouldn't be allowed in the first place.
                # 2005-10-14: we'll not handle this case and it should not turn out too bad.
                children.append((indent,line))
                continue

        if trim_indent == None:
            if line.strip().lower() != tag0:
                # unaffected
                output.append(line)
            else:
                # enter trimming state
                trim_indent = indent
                children = []
                count += 1

    if trim_indent != None:
        _trim_children_and_output(trim_indent, children, output)

    return ''.join(output), count


def _trim_children_and_output(align_column, children, output):
    """ Align children to align_column (shift grandchildren by same amount) """
    if not children:
        return
    # use first child as child_col
    # if the tree is welformed, this would be minimal.
    child_col = children[0][0]
    for col, line in children:
        # notation for blank lines?
        if col == None:
            output.append(line)
            continue
        assert col > align_column
        if col < child_col:
            # This would happen in a deformed tree.
            # Anyway realign to this smaller row
            child_col = col
        line = ' ' * (col - (child_col-align_column)) + line.lstrip()
        output.append(line)




#-----------------------------------------------------------------------

#def merge_DAG(p,q):
#    """
#    Definition
#        r = merge(p,q)
#        for all (v,w) in r <=> (v,w) in p or (v,w) in q
#
#        unless if it forms a cycle!
#    """
#    for vq, nq in q.items():
#
#        np = p.setdefault(vq,[vq,[]])
#
#        for cq,_ in nq[1]:
#            cq = cq
#            # merging (vq,cq) to p
#            for cp,_ in np[1]:
#                # is duplicated edge?
#                if cp == cq:
#                    break
#            else:
#                # add (vq, cq) to np
#                cnp = p.setdefault(cq,[cq,[]])
#                if form_cycle(np, cnp):
#                    print >>sys.stderr, 'reject edge %s -> %s' % (np[0],cnp[0])
#                else:
#                    np[1].append(cnp)
#
#def form_cycle(p,q):
#    """ would adding edge(p,q) form a cycle? """
#    for v, level in dfs(q):
#        if v == p[0]:
#            return True
#    return False
#
#def detect_cycle(root):
#    """ Raise CycleError if cycle found. """
#    for v, path in dfsp(root):
#        try:
#            i = path.index(v)
#            raise CycleError(path[i:]+[v])
#        except ValueError:
#            pass

def find_branches(category_root, tag):
    """
    Build a tree with tag as the root node. Gather directory children
    all over the category under this tree.

    Note: The result tree share objects reference with the category
    tree. Do not modify the tree.
    """
    assert tag
    result = []
    _find_branches1(category_root, tag, result)
    return Node(tag,result)


def _find_branches1(node, tag, result):
    """
    Walk node in dfs order. Whenever tag is found, add its children to
    result and stop traversing down.
    """
    for child in node.children:
        if child.data == tag:
            result.extend(child.children)
        else:
            _find_branches1(child, tag, result)


# ------------------------------------------------------------------------
def topoSort(wlib, g):
    ## TODO: HACKish algorithm
    nlist = g.values()[:]

    for n in nlist:
        if n[0]:        ## '' trouble
            n[0].indegree = 0
            n[0].torder = -1

    for v,children in nlist :
        for c in children:
            if c[0]: ##
                c[0].indegree += 1

    top_nodes = [n for n in nlist if not n[0] or n[0].indegree == 0]

    order = 0
    while top_nodes:
        node = top_nodes.pop(0)
        order += 1
        if node[0]:
            node[0].torder = order
        for cn in node[1]:
            if cn[0]:
                cn[0].indegree -= 1
            if cn[0].indegree == 0:
                top_nodes.append(cn)



# ------------------------------------------------------------------------
DATA = """
C1
  C11
     C111
    C112x
 C12x
"""

def test_parse():
    print 'DATA=' + DATA
    print
    root = parse_text_tree(DATA)
    print 'Tree='
    root.dump()


def test_del():
    print edit_text_tree_delete("""
C1

C2
    C21
    C22

C3""", 'C2')[0]


def test_node():
    root = Node('a', [
        Node('a1'),
        Node('a2'),
        Node('a3', [
            Node('a31'),
            Node('a32'),
        ]),
        Node('a4'),
    ])
    root.dump()



def main(argv):
    #test_del()
    #test_parse()
    test_node()

if __name__ =='__main__':
    main(sys.argv)
