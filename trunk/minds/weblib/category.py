import sys
import sets

from minds import weblib
from minds.weblib import graph
from minds.weblib import store

Node = graph.Node

#-----------------------------------------------------------------------

#class TagRel(object):
#    def __init__(self, tag):
#        self.tag = tag
#        self.node = (self, [])
#        self.node = [self, []]
#        self.num_item = 0
#        self.isTopLevel = True
#        self._related_map = {}  # tag.id -> count, rel
#
#        self.torder = tag.id    # total order of tags, right now just abitrary use tag.id
#
#        tag.rel = self          # HACK~~##
#
#    def __str__(self):
#        return self.tag.__str__()
#
#    def __repr__(self):
#        return self.tag.__repr__()

class Category(object):

    def __init__(self, wlib):
        self.wlib = wlib
        self.root = Node('',[])
        self.uncategorized = []


    def getDescription(self):
        return self.wlib.headers['category_description']


    def setDescription(self, description):
        self.wlib.headers['category_description'] = description


    def renameTag(self, tag0, tag1):
        text= self.getDescription()
        edited, count = graph.edit_text_tree_rename(text, tag0, tag1)
        if count > 0:
            self.setDescription(edited)


    def deleteTag(self, tag0):
        text = self.getDescription()
        edited, count = graph.edit_text_tree_delete(text, tag0)
        if count > 0:
            self.setDescription(edited)


    # TODO: move to util and add test? though it is not used now.
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


    def compile(self):
        """
        Build root and uncategorized from category_description
        and current set of Tags
        """

        # TODO: should countTag in category? clean up.
        self._countTag()

        text = self.getDescription()
        self.root = graph.parse_text_tree(text)

        categorized = sets.Set()
        for node, p in self.root.dfs():
            tag = self.wlib.tags.getByName(node.data)
            if tag:
                # convert string to node
                # TODO: should we not do this? because there is still going to be some non-tag string?
#                node.data = tag
                categorized.add(tag)

        # build uncategorized
        self.uncategorized = [tag for tag in self.wlib.tags if tag not in categorized]
        self.uncategorized = weblib.sortTags(self.uncategorized)


    def _countTag(self):
        # construct tag statistics
        for tag in self.wlib.tags:
            tag.num_item = 0

        for item in self.wlib.webpages:
            for tag in item.tags:
                tag.num_item += 1

#    def inferCategory(wlib):
#
#        R = [TagRel(tag) for tag in wlib.tags]
#
#        # construct tag statistics
#        for item in wlib.webpages:
#            for tag in item.tags:
#                tag.rel.num_item += 1
#                rmap = tag.rel._related_map
#                # loop through otherTag in the same item
#                for otherTag in item.tags:
#                    if otherTag != tag:
#                        count,_ = rmap.setdefault(otherTag.id, (0,otherTag.rel))
#                        rmap[otherTag.id] = count+1,otherTag.rel
#
#        # build subset_by_size for each tag
#        for tRel in R:
#            tRel.related = []
#            tRel.subset_by_size = []
#            for count, rel in tRel._related_map.values():
#                tRel.related.append((count,rel))
#                if count == rel.num_item:               # every item with tag rel also has tag tRel
#                    rel.isTopLevel = False              # i.e. rel is a subset of tRel
#                    size = (rel.num_item, rel.torder)   # for items of same num_item, break by torder
#                                                        # need to maintain consistent total order for knock_off()
#                    tRel.subset_by_size.append((size, rel.node))
#            tRel.related.sort(reverse=True)
#            tRel.subset_by_size.sort(reverse=True)
#
#        node_by_size = [(v.num_item, v.node) for v in R]
#        node_by_size.sort(reverse=True)
#        root = build_DAG(node_by_size)
#
#        for tRel in R:
#            # remove temp data structures to save memory?
#            del tRel.subset_by_size
#            del tRel._related_map
#
#        for tRel in R:
#            tRel.torder = 0
#
#        for i, (v, level) in enumerate(graph.dfs(root)):
#            if not v:
#                continue    # skip the root node
#            if not v.torder:
#                v.torder = i+1
#
#        return root
#
#
#    def build_DAG(node_by_size):
#        """
#        Base on the subset relations construct a DAG.
#        Includes only direct subset (i.e. no transitive closure).
#        """
#        for _, node in node_by_size:                    # iterate nodes from the largest
#            ss = node[0].subset_by_size[:]
#            while ss:                                   # iterate on ss (subset_by_size)
#                _, largest = ss[0]
#                node[1].append(largest)                 # largest is in the direct subset
#                subset2 = largest[0].subset_by_size
#                knock_off(ss, subset2)                  # remove transitive closures via largest
#                ss[0] = None                            # remove largest
#                ss = filter(None,ss)                    # filter removed items
#
#        tops = [node for s, node in node_by_size if node[0].isTopLevel and node[1]]
#        standalone = [node for s, node in node_by_size if node[0].isTopLevel and not node[1]]
#    #    standalone_node = (None, standalone)  ##??
#    #    tops.append(standalone_node)
#        tops.extend(standalone)
#        return ['', tops]                             # return root



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
        italy
money
    account
    real estate
real estate
    listing
    San Francisco
        agents
travel
    italy
        food
"""


def test_tag_tree():
    print '\ntree0---'
    root0 = graph.parse_text_tree(TEST_DATA0)
    root0.dump()

    print '\ntree1---'
    root0 = graph.parse_text_tree(TEST_DATA)
    root0.dump()

    graph.merge_DAG(g0,g)
    print '\nmerged---'
    root0.dump()


def test_DAG():
    wlib = store.getMainBm()
    root = inferCategory(wlib)
    ## debug
    for v, path in root.dfs():
        if not v:
            continue    # skip the root node
        print '..' * len(path) + unicode(v) + ' %s' % v.torder + ' %s' % path


def test_find_branches():
    root = graph.parse_text_tree(TEST_DATA)
    branches = graph.find_branches(root, 'San Francisco')
    print '\nSan Francisco branches---'
    print >>sys.stderr, branches
    Node('',branches).dump()


def main(argv):
    test_find_branches()
    #test_tag_tree()
    #test_DAG()


if __name__ =='__main__':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout,'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr,'replace')
    main(sys.argv)
