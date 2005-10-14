""" Graph utilities

The graphs used here are directed acyclic graphs. Usually there an arbitrary
root node added at the starting point of traversal.

A node is a list of [item, children, other attributes]

where
    item - the vertex, also the payload of the node
    children - a list of child nodes
    others - store attributes used when running algorithms

"""
import sys

#-----------------------------------------------------------------------
# Indented text parsing

class CycleError(Exception): pass

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

    A node is a 2-tuple of [name, list of children)]
    It is represented by list so that the elements can be updated.
    """
    root_node = ['',[]]
#    nodes = {'': root_node}

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
        node = [name,[]]
#        name = name.lower()
#        node = nodes.setdefault(name,[name,[]])

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
        cur_node[1].append(node)

        # the new cur_node
        cur_indent,cur_node = indent,node
        stack.append((cur_indent,cur_node))

    return root_node


def edit_text_tree_rename(data, tag0, tag1):
    """
    tag0 has renamed to tag1.
    Apply the same changed to text tree
    """
    tag0 = tag0.lower()
    output = []
    for line in data.splitlines(True):
        if line.strip().lower() == tag0:
            line = line.lower().replace(tag0,tag1)
        output.append(line)
    return ''.join(output)


def edit_text_tree_delete(data, tag0):
    """
    tag0 has been deleted.
    Apply the same changed to text tree.
    Realign children lines if necessary.
    """
    tag0 = tag0.lower()
    output = []

    trim_row = None     # if in trimming state, indent of trim_row

    for line in data.splitlines(True):
        if line.isspace():
            output.append(line)
            continue

        indent, name = _split_indent(line)

        # trim_row determine if we are in trimming state
        if trim_row != None:
            if len(indent) <= len(trim_row):
                # leave trim mode
                _trim_children_and_output(len(trim_row), children, output)
                trim_row = None
                children = [] # tidy up
            else:
                # TODO: What if this line also contain tag0!!!
                # This is an obvious cycle, shouldn't be allowed in the first place.
                # 2005-10-14: we'll not handle this case and it should not turn out too bad.
                children.append((len(indent),line))
                continue

        if trim_row == None:
            if line.strip().lower() != tag0:
                # unaffected
                output.append(line)
            else:
                # enter trimming state
                trim_row = indent
                children = []

    if trim_row:
        _trim_children(len(trim_row), children, output)

    return ''.join(output)


def _trim_children_and_output(align_column, children, output):
    """ Align children to align_column (shift grandchildren by same amount) """
    if not children:
        return
    # use first child as child_col
    # if the tree is welformed, this would be minimal.
    child_col = children[0][0]
    for col, line in children:
        assert col > align_column
        if col < child_col:
            # This would happen in a deformed tree.
            # Anyway realign to this smaller row
            child_col = col
        line = ' ' * (col - (child_col-align_column)) + line.lstrip()
        output.append(line)


def merge_DAG(p,q):
    """
    Definition
        r = merge(p,q)
        for all (v,w) in r <=> (v,w) in p or (v,w) in q

        unless if it forms a cycle!
    """
    for vq, nq in q.items():

        np = p.setdefault(vq,[vq,[]])

        for cq,_ in nq[1]:
            cq = cq
            # merging (vq,cq) to p
            for cp,_ in np[1]:
                # is duplicated edge?
                if cp == cq:
                    break
            else:
                # add (vq, cq) to np
                cnp = p.setdefault(cq,[cq,[]])
                if form_cycle(np, cnp):
                    print >>sys.stderr, 'reject edge %s -> %s' % (np[0],cnp[0])
                else:
                    np[1].append(cnp)


#-----------------------------------------------------------------------

def dfs_node(root):
    yield root
    for child in root[1]:
        for x in dfs_node(child): yield x


def dfs(root,level=0):
    """ Walk a tree in DFS order, yielding (node,level). """
    yield root[0], level
    for child in root[1]:
        for x in dfs(child,level+1): yield x

def dfsp(root, path=None):
    """ yield (vertex, path to vertex) """

    # create the initial path stack
    # note: don't put this as the default parameter
    if path is None:
        path = []
    else:
        yield root[0], path

    path.append(root[0])
    for child in root[1]:
        for x in dfsp(child,path): yield x
    path.pop()


def dfs_edge(root):
    """ yield (from vertices, to vertices) """
    for child in root[1]:
        yield root[0], child[0]
        for x in dfs_edge(child): yield x


def detect_cycle(root):
    """ Raise CycleError if cycle found. """
    for v, path in dfsp(root):
        try:
            i = path.index(v)
            raise CycleError(path[i:]+[v])
        except ValueError:
            pass


def form_cycle(p,q):
    """ would adding edge(p,q) form a cycle? """
    for v, level in dfs(q):
        if v == p[0]:
            return True
    return False


# ------------------------------------------------------------------------

DATA = """
C1
  C11
     C111
    C112x
 C12x
"""

def main(argv):
    print 'DATA=' + DATA
    print
    root = parse_text_tree(DATA)
    for v, level in dfs(root):
        if v:
            print '..'*level + unicode(v)

if __name__ =='__main__':
    main(sys.argv)
