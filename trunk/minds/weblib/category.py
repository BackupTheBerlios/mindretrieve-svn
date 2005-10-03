import sys
import sets

from minds import weblib
from minds.weblib import graph
from minds.weblib import store


#-----------------------------------------------------------------------

class TagRel(object):
    def __init__(self, tag):
        self.tag = tag
        self.node = (self, [])
        self.node = [self, []]
        self.num_item = 0
        self.isTopLevel = True
        self._related_map = {}  # tag.id -> count, rel

        self.torder = tag.id    # total order of tags, right now just abitrary use tag.id

        tag.rel = self          # HACK~~##

    def __str__(self):
        return self.tag.__str__()

    def __repr__(self):
        return self.tag.__repr__()


def inferCategory(wlib):

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
#    standalone_node = (None, standalone)  ##??
#    tops.append(standalone_node)
    tops.extend(standalone)
    return ['', tops]                             # return root


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


def buildCategory(wlib):
    root = inferCategory(wlib)
#    nodes = {}
#    for node in graph.dfs_node(root):
#        if not nodes.has_key(node[0]):
#            nodes[node[0]] = node

    g0 = graph.build_indented_text_DAG(wlib.category_description)
    g1 = __convert_name_2_trel(wlib, g0)

    #graph.merge_DAG(g1,nodes)

    topoSort(wlib, g1)

    uncategorized = [tag for tag in wlib.tags if not g0.has_key(tag.name.lower())]

    return g1[''], uncategorized


def __convert_name_2_trel(wlib,g):
    g1 = {}
    for v,n in g.items():
        tag = wlib.tags.getByName(v)
        if not tag and v:
            tag = weblib.Tag(name=v)        ## TODO: clean up hack
            wlib.addTag(tag)
            TagRel(tag)
        if tag:
            tRel = tag.rel
            n[0] = tRel
        g1[n[0]] = n
    return g1


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

#    for n in nlist:
#        if n[0]:        ## '' trouble
#            from pprint import pprint
#            pprint(u'%s %s' % (n[0], n[0].indegree),sys.stdout)##

    order = 0
    while top_nodes:
        node = top_nodes.pop(0)
        order += 1
        if node[0]:
            node[0].torder = order
##            print >>sys.stdout, u'## %s %s' % (node[0], node[0].torder)
        for cn in node[1]:
            if cn[0]:
                cn[0].indegree -= 1
            if cn[0].indegree == 0:
                top_nodes.append(cn)



#-----------------------------------------------------------------------


TEST_DATA0 = """
mindretrieve
    search
    python
    web design
    css
travel
    italy
    san francisco
        real estate
"""

TEST_DATA = """
San Francisco
    food
    travel
money
    account
    real estate
real estate
    listing
    San Francisco
travel
    italy
        food
"""

TEST_DATA0= ''

def test_tag_tree():
    g0 = graph.build_indented_text_DAG(TEST_DATA0)
    root0 = g0['']

    print '\ntree0---'
    for v, level in graph.dfs(root0):
        if v:
            print '..'*level + unicode(v)

    g = graph.build_indented_text_DAG(TEST_DATA)
    root = g['']

    print '\ntree1---'
    for v, level in graph.dfs(root):
        if v:
            print '..'*level + unicode(v)

    graph.merge_DAG(g0,g)
    print '\nmerged---'
    for v, level in graph.dfs(root0):
        if v:
            print '..'*level + unicode(v)


def test_DAG():
    wlib = store.getMainBm()
    root = inferCategory(wlib)
    ## debug
    for v, path in graph.dfsp(root):
        if not v:
            continue    # skip the root node
        print '..' * len(path) + unicode(v) + ' %s' % v.torder + ' %s' % path


def test_flex_category():
    wlib = store.getMainBm()
    for v, level in graph.dfs(wlib.categories):
        if v:
            print '..'*level + unicode(v) +' ' + str(v.torder)
    from pprint import pprint
    pprint(wlib.uncategorized)



def main(argv):
    test_flex_category()
    #test_tag_tree()
    #test_DAG()


if __name__ =='__main__':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout,'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr,'replace')
    main(sys.argv)
