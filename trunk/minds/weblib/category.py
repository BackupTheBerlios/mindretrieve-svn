import sys
import sets

from minds import weblib
#from minds.weblib import util
from minds.weblib import graph


TEST_DATA = """
San Francisco
money
tech
    python
        outdoor
    DHTML
        CSS
            
Travel
    outdoor
        DHTML
"""          

def make_tag_tree(wlib, root):
    root_node = (None,[])
    nodes = {'': root_node}  # name -> node(Tag)
    
    for name_v, level in graph.dfs(root):
        name = name_v.lower()        
        if not nodes.has_key(name):
            tag = wlib.tags.getByName(name)
            nodes[name] = (tag,[])
        
    for parent, child in graph.dfs_edge(root):
        pn = nodes[parent.lower()]
        cn = nodes[child.lower()]
        pn[1].append(cn)
        
    for node in nodes.values():
        children = node[1]
        new_children = []
        added = sets.Set()
        for child in children:
            if child[0] not in added:
                added.add(child[0])
                new_children.append(child)

        del children[:]
        children.extend(new_children)
    
    return root_node
    
#def make(wlib, root):
#    children = root[1]
#    children[:] = [(wlib.tags.getByName(name), grandchildren) for name, grandchildren in children]
#    for child in children:
#        make(wlib, child)


def inferGraph(wlib):
    V = {}
    for tag in wlib.tags:
        V[tag] = (tag,[])

    root = ('',[])

    root_nodes = sets.Set(iter(wlib.tags))

    for tag in wlib.tags:
        tag_node = V[tag]
        tag_node[1][:] = [V[child] for child in tag.isTag] 

        root_nodes.difference_update(tag.isTag)

    root[1][:] = [V[tag] for tag in root_nodes]
                
    for v, level in graph.dfs(root):
        print '..'*level + unicode(v)

    
#-----------------------------------------------------------------------

class TagRel(object):
    def __init__(self, tag):
        self.tag = tag
        self.node = (self, [])
        self.num_item = 0
        self.isTopLevel = True
        self._related_map = {}  # tag.id -> count, rel
        
        self.torder = tag.id    # total order of tags, right now just abitrary use tag.id
        
        tag.rel = self          # HACK~~##
        
    def __str__(self):
        return self.tag.__str__()

    def __repr__(self):
        return self.tag.__repr__()
            

def buildCategory(wlib):
    
    R = [TagRel(tag) for tag in wlib.tags]

    # construct tag statistics
    for item in wlib.webpages:
        for tag in item.tags:
            tag.rel.num_item += 1
            rmap = tag.rel._related_map
            # loop through otherTag in the same item
            for otherTag in item.tags:
                if otherTag != tag:
                    count,_ = rmap.setdefault(otherTag.id, (0,otherTag.rel))
                    rmap[otherTag.id] = count+1,otherTag.rel

    # build subset_by_size for each tag
    for tRel in R:
        tRel.related = []
        tRel.subset_by_size = []
        for count, rel in tRel._related_map.values():
            tRel.related.append((count,rel))
            if count == rel.num_item:               # every item with tag rel also has tag tRel
                rel.isTopLevel = False              # i.e. rel is a subset of tRel
                size = (rel.num_item, rel.torder)   # for items of same num_item, break by torder
                                                    # need to maintain consistent total order for knock_off()
                tRel.subset_by_size.append((size, rel.node))
        tRel.related.sort(reverse=True)
        tRel.subset_by_size.sort(reverse=True)
        
    node_by_size = [(v.num_item, v.node) for v in R]
    node_by_size.sort(reverse=True)
    root = build_DAG(node_by_size)

    for tRel in R:
        # remove temp data structures to save memory?
        del tRel.subset_by_size
        del tRel._related_map
    
    for tRel in R:
        tRel.torder = 0
        
    for i, (v, level) in enumerate(graph.dfs(root)):
        if not v:
            continue    # skip the root node
        if not v.torder:
            v.torder = i+1


    return root


def build_DAG(node_by_size):
    """ 
    Base on the subset relations construct a DAG.
    Includes only direct subset (i.e. no transitive closure).
    """
    for _, node in node_by_size:                    # iterate nodes from the largest
        ss = node[0].subset_by_size[:]
        while ss:                                   # iterate on ss (subset_by_size)
            _, largest = ss[0]                      
            node[1].append(largest)                 # largest is in the direct subset
            subset2 = largest[0].subset_by_size
            knock_off(ss, subset2)                  # remove transitive closures via largest
            ss[0] = None                            # remove largest
            ss = filter(None,ss)                    # filter removed items
            
    tops = [node for s, node in node_by_size if node[0].isTopLevel and node[1]]
    standalone = [node for s, node in node_by_size if node[0].isTopLevel and not node[1]]
    standalone_node = (None, standalone)  ##??
    tops.append(standalone_node)
    return [None, tops]                             # return root


def knock_off(S, D):
    """ 
    An efficient method to remove items from S that also appear in D.
    Both S and D should be sorted in decreasing order.
    Removed items are simply set to None.
    """
    i = 0
    j = 0
    while i < len(S) and j < len(D):
        s, d = S[i], D[j]
        ssize, dsize = s[0], d[0]   # ssize and dsize represents the total order of s and d
        result = cmp(ssize,dsize)
        if result == 0:
            S[i] = None
            i += 1
            j += 1
        elif result > 0:
            i += 1
        else:
            j += 1

#-----------------------------------------------------------------------

def test_tag_tree():
    wlib = weblib.getMainBm()
    tree = util.parse_indent_text(TEST_DATA)
    tree = make_tag_tree(wlib, tree)
    # check syntax
    # check non tag
    # check cycle

    cycle = util.find_cycle(tree)
    print cycle
    if cycle:
        raise 'Cycle'
            
    
#    from pprint import pprint
#    pprint(tree)##
    for v, level in graph.dfs(tree):
        print '..'*level + unicode(v)
     
    for v, path in graph.dfsp(tree):    
        print v, path
        
    print util.find_cycle(tree)    
    #inferGraph(wlib)

    
def test_DAG():    
    bm = weblib.getMainBm()
    root = buildCategory(bm)
    ## debug
    for v, path in graph.dfsp(root):
        if not v:
            continue    # skip the root node
        print '..' * len(path) + unicode(v) + ' %s' % v.torder + ' %s' % path


def main(argv):
    #test_tag_tree()
    test_DAG()

            
    
if __name__ =='__main__':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout,'replace')
    main(sys.argv)
