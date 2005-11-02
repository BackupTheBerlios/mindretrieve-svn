""" __init__.py [options] [args]
    -h:     show this help
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
    """ @return:
            cat_list, - tuple of tags -> list of items,
            related,
            most_visited
    """
    terms = _parse_terms(querytxt)
    select_tags_set = sets.Set(select_tags)
    if not terms and not select_tags:
        return queryMain(wlib)

    # if querytxt is an exact match of a tag, include it.
    include_tag = wlib.tags.getByName(querytxt)

    log.debug('Search terms %s tags %s', terms, select_tags)
    cat_list = {}
    related = sets.Set()
    most_visited = None
    for item in wlib.webpages:
        # filter by select_tag
        if select_tags_set and select_tags_set.difference(item.tags):
            continue

        netloc = urlparse.urlparse(item.url)[1].lower()
        if include_tag in item.tags:
            pass
        else:
            q_matched = True
            for w in terms:
                if (w not in item.name.lower()) and (w not in netloc):
                    q_matched = False
                    break
            if not q_matched:
                continue

            # most visited only activates with a querytxt
            if not most_visited or item.lastused > most_visited.lastused:
                most_visited = item

        cat = util.diff(item.tags, select_tags)
        cat2bookmark = cat_list.setdefault(tuple(cat),[])
        cat2bookmark.append(item)
        related.union_update(item.tags)

    related = [(t.num_item, None) for t in related]
    related = [related,[],[]]

    return cat_list, tuple(related), most_visited

def queryMain(wlib):
    """ @return: cat_list, related, random where
            cat_list: tuple of tags -> list of items,
    """
    items = [item for item in wlib.webpages if not item.tags]
    tags = [l for l in wlib.tags]
    ## TODO: need clean up, also should not use private _lst
    random_page = wlib.webpages._lst and random.choice(wlib.webpages._lst) or None
    return {tuple(): items}, (), random_page



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
    tags,unknown = parseTags(wlib, tags)
    if unknown:
        print 'Ignore unknown tags', unknown

    tags_matched = query_tags(wlib, querytxt, tags)
    print 'Tags matched',
    pprint(tags_matched)

    cat_list, related, most_visited = query(wlib, querytxt, tags)

    pprint(tags)

#    pprint(sortTags(related[0]+related[1]+related[2]))

    for key, value in sorted(cat_list.items()):
        sys.stdout.write('\n' + u','.join(map(unicode, key)) + '\n')
        for item in value:
            tags = [tag.name for tag in item.tags]
            print '  %s (%s)' % (unicode(item), ','.join(tags))

    print 'Most visited:', most_visited


def main(argv):
    querytxt = ''
    if len(argv) <= 1:
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
    else:
        testQuery(wlib, querytxt, tags)


if __name__ == '__main__':
    sys.stdout = codecs.getwriter('utf8')(sys.stdout,'replace')
    main(sys.argv)