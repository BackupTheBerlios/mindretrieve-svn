""" __init__.py [options] [args]
    -h:     show this help
    -q:     query querytxt
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
from minds import distillML
from minds import distillparse

log = logging.getLogger('weblib')
TAG_DEFAULT = 'inbox'


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


class Tag(object):

    def __init__(self, id=-1, name=''):

        if not name:
            raise RuntimeError('Tag name required')

        self.id         = id
        self.name       = name

        self.isTag      = []    # isTag is intersection of all tags for all items
        self.related    = {}    # relatedTag -> count, relatedTags is union of all tag for all items
                                # Then inferRelation() would make it a list of tuples???
        self.num_item   = 0

    def __str__(self):
        return self.name

    def __repr__(self):
        return unicode(self)


class WebLibrary(object):

    def __init__(self):
        self.headers = {
            'category_description':'',
            'category_collapse':'',
        }
        # Should contain the keys of self.headers.
        # Use to maintain header order when persist to disk.
        self.header_names = []

        self.webpages = util.IdList()
        self.tags = util.IdNameList()

        import category
        self.category = category.Category(self)

        self.index_writer = None
        self.index_reader = None
        self.index_searcher = None
#        self.init_index()


    def close(self):
        # TODO: well placed?
        if self.index_searcher: self.index_searcher.close()
        if self.index_reader:   self.index_reader.close()
        if self.index_writer:   self.index_writer.close()

    # TODO: weblib use to be quite standalone container class. However, index need to be careful managed and properly closed. FIND A SYSTEM. use store?
    def init_index(self):
        from minds import lucene_logic
        wpath = cfg.getpath('weblibindex')
        self.index_writer = lucene_logic.Writer(wpath)
        self.index_reader = lucene_logic.Reader(wpath)
        self.index_searcher = lucene_logic.Searcher(pathname=wpath)


    def addWebPage(self, entry):
        self.webpages.append(entry)


    def addTag(self, entry):
        self.tags.append(entry)


    def newWebPage(self, name='', url='', description=''):
        """ Create a minimal WebPage for user to fill in.
            @return: a WebPage
        """
        modified = datetime.date.today().isoformat()
        lastused = modified
        return WebPage(
            name        =name,
            url         =url,
            description =description,
            modified    =modified,
            lastused    =lastused,
        )


    def updateWebPage(self, item):
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


    def deleteWebPage(self, item):
        self.webpages.remove(item)


    def getTag(self, name):
        return self.tags.getByName(name)


    def visit(self, item):
        from minds.weblib import store
        item.lastused = datetime.date.today().isoformat()
        ## TODO: optimize!!!
        store.save(self)


    def getDefaultTag(self):
        d = cfg.get('weblib.tag.default', TAG_DEFAULT)
        if not d:
            return None
        tag = self.tags.getByName(d)
        if tag:
            return tag
        # default tag is not previous used; or user has chosen a new default?
        tag = Tag(name=d)
        self.tags.append(tag)
        self.category.compile()
        return tag


    def tag_rename(self, tag, newName):
        log.debug(u'tag_rename tag count=%s tag=%s newName=%s', len(self.tags), unicode(tag), newName)
        oldName = unicode(tag)
        self.tags.rename(tag, newName)
        self.category.renameTag(oldName, newName)


    def tag_merge_del(self, tag, new_tag=None):
        """
        Delete or merge tag
        @param tag - tag to be altered
        @param new_tag - tag to merge with, or None to delete tag.
        """
        log.debug(u'tag_merge_del tag count=%s tag=%s new_tag=%s', len(self.tags), unicode(tag), new_tag)

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

        # merge or delete, old tag would be removed from tags
        self.tags.remove(tag)
        self.category.deleteTag(unicode(tag))
        log.debug('tag_merge_del completed new tag count=%s', len(self.tags))

        self.category.compile()
        # TODO: need to delete it from the category


    def setCategoryCollapse(self, tid, value):
        ids = self.getCategoryCollapseList()
        if value:
            if tid not in ids:
                ids.append(tid)
        else:
            if tid in ids:
                ids.remove(tid)

        # filter out invalid ids
        ids = filter(self.tags.getById, ids)
        ids.sort()

        # TODO: note that CategoryCollapse applies to top level tag only
        # As user edit the category some tag may no longer at top level.
        # Thus it becomes dead value as the user can not udpate it.
        self.headers['category_collapse'] = ','.join(('@%s'%id for id in ids))


    def getCategoryCollapseList(self):
        """ Return list of tag ids configured in category_collapse """
        category_collapse = self.headers['category_collapse']
        category_collapse = category_collapse.replace(' ','')
        if not category_collapse:
            return [] # otherwise split() would give ['']
        lst = []
        for s in category_collapse.split(','):
            if s.startswith('@'):
                try:
                    lst.append(int(s[1:]))
                except ValueError:
                    pass
        lst.sort()
        return lst


#    def categorize(self):
###        """ call this when finished loading """
###
###        # set item.tags from tagIds
###        for item in self.webpages:
###            tags = [self.tags.getById(id) for id in item.tagIds]
###            item.tags = filter(None, tags)
###            # remove tagIds to avoid duplicated data?
#        #TODO: clean this
#        import category
#        # TODO: doc this. What's the structure of categories anyway??
#        self.categories, self.uncategorized = category.buildCategory(self)


# ----------------------------------------------------------------------

def parseTag(wlib, name):
    """ Parse tag names or tag id. Return tag or None. """
    # tag id in the format of @ddd?
    if name.startswith('@') and name[1:].isdigit():
        id = int(name[1:])
        return wlib.tags.getById(id)
    else:
        return wlib.getTag(name)


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


def create_tags(wlib, names):
    """ Return list of Tags created from the names list. """
    lst = []
    for name in names:
        tag = wlib.getTag(name)
        if not tag:
            tag = Tag(name=name)
            wlib.addTag(tag)
        lst.append(tag)
    return lst


def sortTags(tags):
    """ sort tags by name in alphabetical order """
    lst = [(tag.name.lower(), tag) for tag in tags]
    return [pair[1] for pair in sorted(lst)]


# ----------------------------------------------------------------------

def organizeEntries(entries, set_tags, add_tags, remove_tags):
    """
    Organize tags of for the entries
    @param entries - list of entries
    @param set_tags - set each entry to tags
    @param add_tags - add tags to each entry
    @param remove_tags - remove tags from each entry

    Caller should ensure ensure the parameters are logical.
    E.g.
        set_tags should be exclusive to add_tags and remove_tags,
        add_tags and remove_tags should have no common elements.
    """
    add_tags = sets.Set(add_tags)
    for item in entries:
        if set_tags:
            item.tags = set_tags[:]
        if add_tags:
            tags = add_tags.union(item.tags)
            item.tags = list(tags)
        if remove_tags:
            item.tags = [t for t in item.tags if t not in remove_tags]


#----------------------------------------------------------------------
# Query

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

    log.debug('Search terms %s tags %s', terms, select_tags)
    cat_list = {}
    related = sets.Set()
    most_visited = None
    for item in wlib.webpages:
        # filter by select_tag
        if select_tags_set and select_tags_set.difference(item.tags):
            continue

        netloc = urlparse.urlparse(item.url)[1].lower()
        if terms:
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

##    if select_tags: ##hack
##        related = analyzeRelated(select_tags[0],related)
##        print >>sys.stderr, related
##    else:
##        related = [(t.rel.num_item, t.rel) for t in related]
##        related = [related,[],[]]

    related = [(t.num_item, None) for t in related]
    related = [related,[],[]]

    return cat_list, tuple(related), most_visited

##refactor
##def analyzeRelated(tag,related):
##    parents, children, others = [],[],[]
##    for count, rel in tag.rel.related:
##        if count == tag.rel.num_item:
##            parents.append((rel.torder, rel))
##        elif count == rel.num_item:
##            children.append((rel.torder, rel))
##        else:
##            pe = 100 * count / tag.rel.num_item
##            ce = 100 * count / rel.num_item
##            x =  (pe+ce,pe,ce)
##            others.append((x, rel))
##    parents.sort()
##    children.sort()
##    others.sort(reverse=True)
##
##    return (parents, children, others)


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

    pprint(sortTags(related[0]+related[1]+related[2]))

    for key, value in sorted(lst.items()):
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

    tags = len(argv) > 1 and argv[1] or ''

    wlib = store.getMainBm()
    testQuery(wlib, querytxt, tags)


if __name__ == '__main__':
    sys.stdout = codecs.getwriter('utf8')(sys.stdout,'replace')
    main(sys.argv)