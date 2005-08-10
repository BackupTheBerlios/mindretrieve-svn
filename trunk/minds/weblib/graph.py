""" Graph utilities

The graphs used here are directed acyclic graphs. Usually there an arbitrary 
root node added at the starting point of traversal.

A node is a list of [item, children, other attributes]

where
    item - the vertex, also the payload of the node
    children - a list of child nodes
    others - store attributes used when running algorithms

"""

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
        
        
def parse_indent_text(data):
    """
    Parse input of indented text into a tree of nodes.
    Return the root node.
    
    A node is tuple of (name, list of children).
    """
    # create the root node
    root_node = ('',[])
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
        node = (name,[])
        if indent == cur_indent:
            # 2nd last in the stack would be the parent
            # note: -1 < 0 <= indent == cur_indent
            # i.e. there is at least 2 items in the stack
            stack.pop() 
            cur_indent, cur_node = stack[-1]
        elif indent > cur_indent:
            # cur_node would be the parent
            pass
        else:
            # find parent with smaller indent
            while indent <= cur_indent:
                # note: -1 < 0 <= indent <= cur_indent
                # i.e. there is at least 2 items in the stack
                stack.pop()
                cur_indent, cur_node = stack[-1]
            # note: should check that indent == cur_indent here.
            # otherwise the text's indentation is invalid.

        # append to parent
        cur_node[1].append(node)

        # this is the new cur_node
        cur_indent,cur_node = indent,node
        stack.append((cur_indent,cur_node))

    return root_node


#-----------------------------------------------------------------------

def dfs(root,level=0):
    """ Walk a tree in DFS order, yielding (node,level). """
    yield root[0], level
    for child in root[1]:
        for r in dfs(child,level+1):
            yield r

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
        for r in dfsp(child,path):
            yield r
    path.pop()


def dfs_edge(root):
    """ yield (from vertices, to vertices) """
    for child in root[1]:
        yield root[0], child[0]
        for r in dfs_edge(child):
            yield r


def find_cycle(root):
    """ Return list of vertices that form a cycle. None if acyclic. """
    for v, path in dfsp(root):
        try:
            i = path.index(v)
            return path[i:]+[v]
        except ValueError:
            pass
    return None



