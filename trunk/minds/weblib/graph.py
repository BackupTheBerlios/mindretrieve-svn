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
        
        
def build_indented_text_DAG(data):
    """
    Parse input of indented text into a graph of nodes.
xx    Return the root node.
    
xx    A node is tuple of (name, list of children).
    """
    # create the root node
    root_node = ['',[]]
    nodes = {'': root_node}
    
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
        name = name.lower()
        node = nodes.setdefault(name,[name,[]])
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

        # the new cur_node
        cur_indent,cur_node = indent,node
        stack.append((cur_indent,cur_node))

    detect_cycle(root_node)

    return nodes


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


#def get_nodes(root):
#    nodes = {}
#    for node in dfs_node(root):
#        if not nodes.has_key(node[0]):
#            nodes[node[0]] = node
#    return nodes
#
#        
