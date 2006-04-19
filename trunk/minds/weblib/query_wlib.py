""" __init__.py [options] [args]
    -h:     show this help
    -a:     show all
    -q:     query querytxt
    -t:     query tag
    -u:     query URL
"""

import codecs
import datetime
import logging
import os.path
import random
import sets
import string
import StringIO
import sys
import urlparse

from minds.config import cfg
from minds import weblib
from minds.weblib import util
from minds.weblib import mhtml
from minds.weblib import graph
from minds.weblib import store

log = logging.getLogger('wlib.qry')

def find_url(wlib, url):
    """
    @url - url to search for. String matching, no normalization.
    @return list of matched WebPages
    """
    if util.isFileURL(url):
        # use a for flexible match rule to account for file name variations.
        ### TODO: NT specific?
        ### TODO: need optimize?
        scheme, netloc, url_path, _, _, _ = urlparse.urlparse(url)
        pathname = util.nt_url2pathname(url_path)
        pathname = os.path.normcase(pathname)
        result = []
        for item in wlib.webpages:
            scheme, netloc, url_path, _, _, _ = urlparse.urlparse(item.url)
            if scheme != 'file':
                continue
            p1 = util.nt_url2pathname(url_path)
            p1 = os.path.normcase(p1)
            if pathname == p1:
                result.append(item)
        return result

    else:
        return [item for item in wlib.webpages if item.url == url]


def _parse_terms(s):
    """ break down input into search terms """
    s = s.lower()
    # TODO: use pyparsing to parse quotes
    return map(string.strip, s.split())


def query_tags(wlib, querytxt, select_tags):
    """ find list of tag that match querytxt """
    terms = _parse_terms(querytxt)
    if not select_tags:
        select_tags = wlib.tags
    result = []
    for tag in select_tags:
        tagname = tag.name.lower()
        for w in terms:
            if w in tagname:
                result.append(tag)
                break
    return result


def query(wlib, querytxt, select_tags):
    """
    @return - sorted list of (webpage, score)
    """
    querytxt = querytxt.lower()
    terms = _parse_terms(querytxt)
    select_tags_set = sets.Set(select_tags)
    if not terms:
        return queryRoot(wlib)

    result = [] # list of (score, active_score, Webpage)

    nickname_score = 100.0
    name_score = 10.0 / len(terms)
    domain_score = 1.0 /len(terms)

    for item in wlib.webpages:
        # first filter by select_tag
        if select_tags_set and select_tags_set.difference(item.tags):
            continue

        score = 0

        if item.nickname.lower() == querytxt:
            score += nickname_score

        lname = item.name.lower()
        for w in terms:
            if w in lname:
                score += name_score

        if score == 0:
            # Secondly check domain name
            # Note we don't do this if name already matched
            # We'll leave score level and let activity determine ranking.
            lnetloc = urlparse.urlparse(item.url)[1].lower()
            for w in terms:
                if w in lnetloc:
                    score += domain_score
                    break

        if score == 0:
            continue

        # add a match
        score = score/len(terms)  # normalize score
        r = (score, item.lastused, item)
        result.append(r)

    result.sort(reverse=True)
    result = [(item, (s1,s2)) for s1,s2,item in result]
    return result


def queryRoot(wlib):
    """
    A special case to round up items with no tags
    """
    return [item for item in wlib.webpages if not item.tags]



#------------------------------------------------------------------------

"""
     A
    / \
   B   C
  / \   \
 C   D   E


Positions

Prefix  Name
----------------------------
        A
1       B
1.1     C
1.2     D
2       C
2.1     E

"""
class Position(graph.Node):

    # Position are nodes that make up a tag tree
    # positions is a linear list in dfs order

    def __init__(self, tag):
        graph.Node.__init__(self, tag)          # data is redundant?
        self.prefix = ''
        self.tag = tag                          # maybe None
        self.parent_path = []                   # path is [Position]
        self.items = []                         # list of Spots
                                                # Spot is tuple of (pos_rel, itags, webpage)

        # field for the trail marking algorithm
        self.trail_walked = False

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return u'%s %s (%s)' % (self.prefix, unicode(self.tag), len(self.items))


def query_by_tag(wlib, tag):
    """
    @return - list of Position with items filled.
    """

    branches = graph.find_branches(wlib.category.root, tag)
    assert branches

    positions = []
    tag_set = sets.Set()    # all tags

    # build positions
    for visit_record in branches.dfs_ctx():
        node, idx, path, _ = visit_record
        pos = Position(node.data)
        positions.append(pos)
        visit_record[3] = pos

        # set prefix, set parent.children
        parent_vr = path and path[-1] or None
        if parent_vr:
            if len(path) == 1:
                pos.prefix = str(idx+1)
            else:
                pos.prefix = '%s.%s' % (path[-1][3].prefix, str(idx+1))
            parent_vr[3].children.append(pos)

        # set parent_path
        pos.parent_path = [vr[3] for vr in reversed(path)]

        # update tag_set
        if pos.tag:
            tag_set.add(pos.tag)

    # note: branches is a non null Tree
    root_pos = positions[0]

    #for pos in positions: print pos # DBEUG
    #for pos, _ in root_pos.dfs(): print pos # DEBUG

    pos_rbfs = [pos for pos,_ in root_pos.bfs()]
    pos_rbfs.reverse()

    for page in wlib.webpages:
        # basic filtering
        rtags = []  # relevant tags
        itags = []  # irrelevant tags
        for tag in page.tags:
            if tag in tag_set:
                rtags.append(tag)
            else:
                itags.append(tag)
        if not rtags:
            continue

        itags.sort()

        for pos in positions:           # clear markers first
            pos.trail_walked = False
        for pos in pos_rbfs:
            if pos.trail_walked:
                continue
            if pos.tag not in rtags:
                continue
            # should insert item in this position
            # calculate pos_rel with respect to this position
            pos_rel = []
            for ppos in pos.parent_path:
                ppos.trail_walked = True
                if ppos.tag in rtags:
                    pos_rel.append(0)
                else:
                    pos_rel.append(1)

            pos.items.append((pos_rel, itags, page))                    # TODO: between pos_rel and itags is irrelevant tag in tree.

    for pos in positions:
        pos.items.sort()

    return positions


# ----------------------------------------------------------------------
# Command line

from pprint import pprint

def testShowAll():
    wlib = store.getWeblib()
    for item in wlib.webpages:
        tags = [tag.name for tag in item.tags]
        print '%s (%s)' % (item.name, ','.join(tags))


def test_find_url(url):
    wlib = store.getWeblib()
    pprint(find_url(wlib, url))


def testQuery(wlib, querytxt, tags):
    tags,unknown = weblib.parseTags(wlib, tags)
    if unknown:
        print 'Ignore unknown tags', unknown

    result = query(wlib, querytxt, tags)

    for item, score in result:
        tags = [tag.name for tag in item.tags]
        print '  %s [%s] (%s)' % (unicode(item), score, ','.join(tags))


def main(argv):
    tags = None
    url = None
    querytxt = ''
    if len(argv) <= 1:
        pass
    elif argv[1] == '-a':
        testShowAll()
        sys.exit(0)
    elif argv[1] == '-h':
        print __doc__
        sys.exit(-1)
    elif argv[1] == '-q':
        querytxt = argv[2]
        del argv[:2]
    elif argv[1] == '-t':
        tags = argv[2]
        del argv[:2]
    elif argv[1] == '-u':
        url = argv[2]
        del argv[:2]

    from minds.weblib import store
    wlib = store.getWeblib()

    if tags:
        tags, unknown = weblib.parseTags(wlib, tags)
        positions = query_by_tag(wlib, tags[0])
        for pos in positions:
            pos.items.sort()
            print pos
            for i in pos.items:
                print '  ' + str(i)

    elif url:
        test_find_url(url)

    elif querytxt:
        testQuery(wlib, querytxt, '')

    else:
        pprint(queryRoot(wlib))


if __name__ == '__main__':
    sys.stdout = codecs.getwriter('utf8')(sys.stdout,'replace')
    sys.stderr = codecs.getwriter('utf8')(sys.stderr,'replace')
    main(sys.argv)