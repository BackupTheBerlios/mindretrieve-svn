"""
Define Weblib data type Tag, WebPage and the container WebLibrary.
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


class WebLibrary(object):

    def __init__(self, store=None):

        self.store = store

        # default headers
        self.headers = {
            'weblib-version':       '0.5',
            'encoding':             'utf8',
            'category_description': '',
        }
        # Should contain the keys of self.headers.
        # Use to maintain header order when persist to disk.
        self.header_names = [
            'weblib-version',
            'encoding',
            'category_description',
        ]

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


    # TODO: can we phrase this out and force people to use minds_lib??
#    def addWebPage(self, entry):
#        if entry.id == -1:
#            # TODO: HACK HACK HACK
#            # logWriteItem need a real id, append it now ot get one. It will be overwritten.
#            self.webpages.append(entry)
#        from minds.weblib import store
#        store.store.logWriteItem(self, entry)

    # TODO: can we phrase this out and force people to use minds_lib??
#    def addTag(self, entry):
#        if entry.id == -1:
#            # TODO: HACK HACK HACK
#            # logWriteItem need a real id, append it now ot get one. It will be overwritten.
#            self.tags.append(entry)
#        from minds.weblib import minds_lib
#        minds_lib.store.logWriteItem(self, entry)


    # TODO: just put this in the CGI
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


#    def deleteWebPage(self, item):
#        self.webpages.remove(item)


    # ------------------------------------------------------------------------
    # Tag methods

# TODO: remove this, it is too novel
    def getTag(self, name):
        return self.tags.getByName(name)


    def visit(self, item):
        item.lastused = datetime.date.today().isoformat()
        self.store.writeWebPage(item)


    def getDefaultTag(self):
        d = cfg.get('weblib.tag.default', TAG_DEFAULT)
        if not d:
            return None
        tag = self.tags.getByName(d)
        if tag:
            return tag
        # default tag is not previous used; or user has chosen a new default?
        tag = Tag(name=d)
        self.store.writeTag(tag)
        self.category.compile()
        return tag


    def tag_rename(self, tag, newName):
        log.debug(u'tag_rename tag count=%s tag=%s newName=%s', len(self.tags), unicode(tag), newName)
        newTag = tag.__copy__()
        newTag.name = newName
        self.store.writeTag(newTag)
        self.category.renameTag(tag.name, newName)


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
            self.store.writeWebPage(item, flush=False)

        self.store.flush()

        # merge or delete, old tag would be removed from tags
        self.store.removeTag(tag)
        log.debug('tag_merge_del completed new tag count=%s', len(self.tags))

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


#    def getCategoryCollapseList(self):
#        """ Return list of tag ids configured in category_collapse """
#        category_collapse = self.headers['category_collapse']
#        category_collapse = category_collapse.replace(' ','')
#        if not category_collapse:
#            return [] # otherwise split() would give ['']
#        lst = []
#        for s in category_collapse.split(','):
#            if s.startswith('@'):
#                try:
#                    lst.append(int(s[1:]))
#                except ValueError:
#                    pass
#        lst.sort()
#        return lst


    # ------------------------------------------------------------------------
    # Webpage methods



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
    from minds.weblib import store
    stor = store.getStore()
    lst = []
    for name in names:
        tag = wlib.getTag(name)
        if not tag:
            tag = Tag(name=name)
            stor.writeTag(tag)
        lst.append(tag)
    return lst


def sortTags(tags):
    """ sort tags by name in alphabetical order """
    lst = [(tag.name.lower(), tag) for tag in tags]
    return [pair[1] for pair in sorted(lst)]


# ----------------------------------------------------------------------

# TODO: put this inside wlib like tag_merge?

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
    stor = store.getStore()
    add_tags = sets.Set(add_tags)
    for item in entries:
        if set_tags:
            item.tags = set_tags[:]
        if add_tags:
            tags = add_tags.union(item.tags)
            item.tags = list(tags)
        if remove_tags:
            item.tags = [t for t in item.tags if t not in remove_tags]
        print >>sys.stderr, '##', 'writeitem', repr(item).encode('ascii','replace')
        stor.writeWebPage(item)

