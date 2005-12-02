"""
Define Weblib data type Tag, WebPage and the container WebLibrary.
"""

# TODO: weblib use to be quite standalone container class. However, index need to be careful managed and properly closed. FIND A SYSTEM. use store?
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
from minds.weblib import graph
from minds.weblib import mhtml
from minds.weblib import util
from minds import distillML
from minds import distillparse

log = logging.getLogger('weblib')
TAG_DEFAULT = 'inbox'


# ------------------------------------------------------------------------

class WebPage(object):

    def __init__(self, id=-1,
        name        ='',
        url         ='',
        description ='',
        tags        =[],
        modified    ='',
        lastused    ='',
        cached      ='',
        archived    ='',
        flags       ='',
    ):
        # put all parameter values as instance variable
        self.__dict__.update(locals())
        del self.self

    def __copy__(self):
        item = WebPage(
            id          = self.id           ,
            name        = self.name         ,
            url         = self.url          ,
            description = self.description  ,
            tags        = self.tags[:]      ,
            modified    = self.modified     ,
            lastused    = self.lastused     ,
            cached      = self.cached       ,
            archived    = self.archived     ,
            flags       = self.flags        ,
        )
        return item

    def __str__(self):
        return self.name

    def __repr__(self):
        return u'%s (%s) %s' % (self.name, ', '.join(map(unicode,self.tags)), self.url)


# ------------------------------------------------------------------------

class Tag(object):

    def __init__(self, id=-1, name='', description='', flags=''):

        if not name:
            raise RuntimeError('Tag name required')

        self.id         = id
        self.name       = name
        self.description= description
        self.flags      = flags

        # TODO: are these still used???
        self.isTag      = []    # isTag is intersection of all tags for all items
        self.related    = {}    # relatedTag -> count, relatedTags is union of all tag for all items
                                # Then inferRelation() would make it a list of tuples???
        self.num_item   = 0

    def __copy__(self):
        tag = Tag(
            id          = self.id           ,
            name        = self.name         ,
            description = self.description  ,
            flags       = self.flags        ,
        )
        return tag

    def match(self, tagOrName):
        # match name case insensitively
        return self.name.lower() == unicode(tagOrName).lower()

    def __str__(self):
        return self.name

    def __repr__(self):
        return unicode(self)


# ------------------------------------------------------------------------

class Category(object):

    def __init__(self, wlib):
        self.wlib = wlib
        self.root = graph.Node('',[])
        self.uncategorized = []


    def getDescription(self):
        return self.wlib.headers['category_description']


    def setDescription(self, description):
        self.wlib.store.writeHeader('category_description', description)


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
        self.uncategorized = sortTags(self.uncategorized)


    def _countTag(self):
        # construct tag statistics
        for tag in self.wlib.tags:
            tag.num_item = 0

        for item in self.wlib.webpages:
            for tag in item.tags:
                tag.num_item += 1


# ------------------------------------------------------------------------

# 2005-12-02 note: index code below is not working

class WebLibrary(object):

    def __init__(self, store):

        self.store = store

        # headers
        self.headers = {}
        self.header_names = []      # ordered list of keys of self.headers

        # default headers
        from minds.weblib import store as store_module
        self.setHeader('weblib-version', store_module.VERSION)
        self.setHeader('encoding', 'utf8')
        self.setHeader('category_description','')

        self.webpages = util.IdList()
        self.tags = util.IdNameList()

        self.category = Category(self)

        self.index_writer = None
        self.index_reader = None
        self.index_searcher = None
#        self.init_index()


    def close(self):
        # TODO: well placed?
        if self.index_searcher: self.index_searcher.close()
        if self.index_reader:   self.index_reader.close()
        if self.index_writer:   self.index_writer.close()


    def init_index(self):
        from minds import lucene_logic
        wpath = cfg.getpath('weblibindex')
        self.index_writer = lucene_logic.Writer(wpath)
        self.index_reader = lucene_logic.Reader(wpath)
        self.index_searcher = lucene_logic.Searcher(pathname=wpath)


    # TODO: this is not used right now
    def updateWebPage(self, item):
        """
        The item updated can be new or existing.
        """
        print >>sys.stderr, '## index %s' % item.name
        return
        self._delete_index(item)
        scontent = self._get_snapshot_content(item)
        print >>sys.stderr, '## ss [%s]' % scontent[:50]
        content = '\n'.join([
            item.name,
            item.description,
            scontent,
        ])

        self.index_writer.addDocument(
            item.id,
            dict(
                uri=item.url,
                date='',
                ),
            content,
        )    # todo date


    def _get_snapshot_content(self, item):
        # TODO: refactor
        filename = item.id == -1 and '_.mhtml' or '%s.mhtml' % item.id
        spath = cfg.getpath('weblibsnapshot')/filename
        if not spath.exists():
            return ''

        fp = spath.open('rb')       # TODO: check file exist, move to weblib? getSnapshotFile()?
        lwa = mhtml.LoadedWebArchive(fp)
        resp = lwa.fetch_uri(lwa.root_uri)
        if not resp:
            return ''

        # TODO: lucene_logic: use to docid is confusing with lucene's internal docid?
        # TODO: mind content-type, encoding, framed objects??
        data = resp.read()
        meta = {}
        contentBuf = StringIO.StringIO()
        result = distillML.distill(resp, contentBuf, meta=meta)
        contentBuf.seek(0)
        # TODO: what's the deal with writeHeader?
        meta, content = distillparse.parseDistillML(contentBuf, writeHeader=None)
        return content


    def _delete_index(self, item):
        print >>sys.stderr, '##index_reader.numDocs(): %s' % self.index_reader.numDocs()
        if self.index_reader.numDocs() > 0:
            import PyLucene
#            term = PyLucene.Term('docid', item.id)
#            n = self.index_reader.deleteDocuments(term)  # IndexReader.delete(Term)?
#            print >>sys.stderr, '##deleted docid=%s: %s' % (item.id, n)



    # ------------------------------------------------------------------------
    # Header methods

    def setHeader(self, name, value):
        if name not in self.header_names:
            self.header_names.append(name)
        self.headers[name] = value


    # ------------------------------------------------------------------------
    # Tag methods

    def getDefaultTag(self):
        d = cfg.get('weblib.tag.default', TAG_DEFAULT)
        if not d:
            return None
        tag = self.tags.getByName(d)
        if tag:
            return tag
        # default tag is not previous used; or user has chosen a new default?
        self.store.writeTag(Tag(name=d))
        self.category.compile()
        # query default tag again
        return self.tags.getByName(d)


    def tag_rename(self, tag, newName):
        log.debug(u'tag_rename tag count=%s tag=%s newName=%s', len(self.tags), unicode(tag), newName)
        oldName = tag.name
        newTag = tag.__copy__()
        newTag.name = newName
        self.store.writeTag(newTag)
        self.category.renameTag(oldName, newName)
        self.category.compile()


    def tag_merge_del(self, tag, new_tag=None):
        """
        Delete or merge tag
        @param tag - tag to be altered
        @param new_tag - tag to merge with, or None to delete tag.
        """
        log.debug(u'tag_merge_del %s-->%s #tag=%s', unicode(tag), new_tag, len(self.tags))
        assert tag in self.tags
        assert not new_tag or new_tag in self.tags

        # collect changed items in updated
        updated = []

        # remove the use of tag from webpages
        for item in self.webpages:
            if tag not in item.tags:
                continue
            if not new_tag:
                # delete tag
                item.tags.remove(tag)
            elif new_tag in item.tags:
                # have both tag and new_tag, merge
                item.tags.remove(tag)
            else:
                # have only tag, merge tag into newTag
                item.tags.remove(tag)
                item.tags.append(new_tag)
            updated.append(item)

        # note: store.writeWebPage udpate wlib.webpages.
        # can't call it while iterating webpages.
        for item in updated:
            self.store.writeWebPage(item, flush=False)

        # merge or delete, old tag would be removed either case
        self.store.removeItem(tag, flush=True)

        log.debug('tag_merge_del completed. Webpages updated=%s #tag=%s', len(updated), len(self.tags))

        # Should we leave the tag in the category for manual clean up?
        # Automatic collapsing category may not be a good idea.
        self.category.deleteTag(unicode(tag))
        self.category.compile()


    def setCategoryCollapse(self, tid, value):
        """ value will toggle the Category Collapse flag 'c' """
        tag = self.tags.getById(tid)
        if not tag:
            log.warn('setCategoryCollapse() tag not found: %s' % tid)
            return
        if value:
            if 'c' not in tag.flags:
                tag.flags += 'c'
        else:
            tag.flags = tag.flags.replace('c','')
        self.store.writeTag(tag)


    # ------------------------------------------------------------------------
    # Webpage methods

    def visit(self, item):
        item.lastused = datetime.date.today().isoformat()
        return self.store.writeWebPage(item)


    def editTags(self, webpages, set_tags, add_tags, remove_tags):
        """
        Edit tags for multiple webpages
        @param webpages - list of webpage
        @param set_tags - set each item to tags
        @param add_tags - add tags to each item
        @param remove_tags - remove tags from each item

        Caller should ensure ensure the parameters are logical.
        E.g.
            set_tags should be exclusive to add_tags and remove_tags,
            add_tags and remove_tags should have no common elements.
        """
        assert not [tag for tag in set_tags if tag not in self.tags]
        assert not [tag for tag in add_tags if tag not in self.tags]
        assert not [tag for tag in remove_tags if tag not in self.tags]
        add_tags = sets.Set(add_tags)
        for item in webpages:
            if set_tags:
                item.tags = set_tags[:]
            if add_tags:
                tags = add_tags.union(item.tags)
                item.tags = list(tags)
            if remove_tags:
                item.tags = [t for t in item.tags if t not in remove_tags]
            self.store.writeWebPage(item)


# ----------------------------------------------------------------------

def parseTag(wlib, nameOrId):
    """ Parse tag names or tag id. Return tag or None. """
    # tag id in the format of @ddd?
    if nameOrId.startswith('@') and nameOrId[1:].isdigit():
        id = int(nameOrId[1:])
        return wlib.tags.getById(id)
    else:
        return wlib.tags.getByName(nameOrId)


def parseTags(wlib, tag_names):
    """
    Parse comma separated tag names.
    @return: list of tags and list of unknown tag names.
    """
    tags = []
    unknown = []
    for name in tag_names.split(','):
        name = name.strip()
        if not name:
            continue
        tag = parseTag(wlib, name)
        if tag:
            tags.append(tag)
        else:
            unknown.append(name)
    tags.sort()
    return tags, unknown

# this is only used in weblibMultiForm.doPost. Move it there.
def create_tags(wlib, names):
    """ Return list of Tags created from the names list. """
    from minds.weblib import store
    stor = store.getStore()
    lst = []
    for name in names:
        tag = wlib.tags.getByName(name)
        if not tag:
            tag = Tag(name=name)
            stor.writeTag(tag)
        lst.append(tag)
    return lst


def sortTags(tags):
    """ sort tags by name in alphabetical order """
    lst = [(tag.name.lower(), tag) for tag in tags]
    return [pair[1] for pair in sorted(lst)]


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
    wlib = store.getWeblib()
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
    graph.Node('',branches).dump()


def main(argv):
    test_find_branches()
    #test_tag_tree()
    #test_DAG()


if __name__ =='__main__':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout,'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr,'replace')
    main(sys.argv)
