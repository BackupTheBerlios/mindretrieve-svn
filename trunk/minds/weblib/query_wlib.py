""" __init__.py [options] [args]
    -h:     show this help
    -a:     show all
    -q:     query querytxt
    -t:     query tag
"""

# TODO: how do I make sure WebPage fields is the right type? e.g. id is int.
# date fields: modified, cached, accessed

import codecs
import datetime
import logging
import random
import sets
import string
import StringIO
import sys
import urlparse

from minds.config import cfg
from minds.util import dsv
from minds import weblib
from minds.weblib import util
from minds.weblib import mhtml
from minds.weblib import graph

log = logging.getLogger('wlib.qry')

def find_url(wlib, url):
    """
    @url - url to search for. String matching, no normalization.
    @return list of matched WebPages
    """
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


def query_by_tag(wlib, tag):
    # TODO: document result returned

    branches = graph.find_branches(wlib.category.root, unicode(tag))
    #branches.dump()

    # TODO: level is a crude method. Should have some path analysis to let item goes into most specific level.

    tag_tree_index = {} # tag id -> (tag, level, result_list)
    for node, level in branches.bfs():
        name = node.data
        tag = wlib.tags.getByName(name)
        if not tag:
            continue
        tree_entry = tag_tree_index.get(tag.id, None)
        if tree_entry and tree_entry.level >= level:
            continue
        tag_tree_index[tag.id] = (tag, level, [])

    # query all webpages
    for entry in wlib.webpages:
        tree_entry = None
        for tag in entry.tags:
            e = tag_tree_index.get(tag.id,None)
            if not e:
                continue
            if not tree_entry or tree_entry[1] < e[1]:
                tree_entry = e
        if tree_entry:
            tree_entry[2].append(entry)

    result = _attach_result(branches, wlib, tag_tree_index)
    return result


def _attach_result(branches, wlib, tag_tree_index):
    """ Build a parallel tree with result attached to corresponding node """
    name = branches.data
    tag = wlib.tags.getByName(name)
    if not tag:
        result = []
    else:
        result = tag_tree_index[tag.id][2]
    new_node = graph.Node((name, result),[])
    for child in branches.children:
        new_node.children.append(_attach_result(child, wlib, tag_tree_index))
    return new_node


def query(wlib, querytxt, select_tags):
    """
    @return - sorted list of (webpage, score)
    """
    querytxt = querytxt.lower()
    terms = _parse_terms(querytxt)
    select_tags_set = sets.Set(select_tags)
    if not terms:
        return queryMain(wlib)

    result = [] # list of (score, active_score, Webpage)

    for item in wlib.webpages:
        # first filter by select_tag
        if select_tags_set and select_tags_set.difference(item.tags):
            continue

        score = 0

        lname = item.name.lower()
        for w in terms:
            if w in lname:
                score += 10

        if score == 0:
            # Secondly check domain name
            # Note we don't do this if name already matched
            # We'll leave score level and let activity determine ranking.
            lnetloc = urlparse.urlparse(item.url)[1].lower()
            for w in terms:
                if w in lnetloc:
                    score += 1
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



# ----------------------------------------------------------------------
# Command line

from pprint import pprint

def testShowAll():
    from minds.weblib import store
    wlib = store.getMainBm()
    for item in wlib.webpages:
        tags = [tag.name for tag in item.tags]
        print '%s (%s)' % (item.name, ','.join(tags))


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

    from minds.weblib import store
    wlib = store.getMainBm()

    if tags:
        branches = query_by_tag(wlib, tags)
        for node, path in branches.dfs():
            name, result = node.data
            print '..'*len(path) + name
            for item in result:
                print u'%s  %s' % ('  '*len(path), item)
    elif querytxt:
        testQuery(wlib, querytxt, '')
    else:
        pprint(queryRoot(wlib))


if __name__ == '__main__':
    sys.stdout = codecs.getwriter('utf8')(sys.stdout,'replace')
    main(sys.argv)