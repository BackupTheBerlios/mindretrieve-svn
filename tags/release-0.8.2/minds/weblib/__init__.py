"""
Define Weblib data type Tag, WebPage and the container WebLibrary.
"""

# TODO: weblib use to be quite standalone container class. However, index need to be careful managed and properly closed. FIND A SYSTEM. use store?

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
from minds.weblib import graph
from minds.weblib import mhtml
from minds.weblib import util
from minds import distillML
from minds import distillparse

log = logging.getLogger('weblib')
TAG_DEFAULT = 'inbox'


# ------------------------------------------------------------------------

class WebPage(object):

    def __init__(self,
        id          =-1,
        timestamp   ='',
        version     =0,
        name        ='',
        nickname    ='',
        url         ='',
        description ='',
        tags        =[],
        created     ='',
        modified    ='',
        lastused    ='',
        fetched     ='',
        flags       ='',
        ):
        self.id          = id
        self.timestamp   = timestamp
        self.version     = version
        self.name        = name
        self.nickname    = nickname
        self.url         = url
        self.description = description
        self.tags        = tags[:]
        self.created     = created
        self.modified    = modified
        self.lastused    = lastused
        self.fetched     = fetched
        self.flags       = flags
        # This serve as a place holder for a string tags description for
        # editing (e.g. from web form). Once it is finalized it should
        # be converted into the list of object references in tags.
        self.tags_description = None

    def __copy__(self):
        item = WebPage(
            id          = self.id           ,
            timestamp   = self.timestamp    ,
            version     = self.version      ,
            name        = self.name         ,
            nickname    = self.nickname     ,
            url         = self.url          ,
            description = self.description  ,
            tags        = self.tags[:]      ,
            created     = self.created      ,
            modified    = self.modified     ,
            lastused    = self.lastused     ,
            fetched     = self.fetched      ,
            flags       = self.flags        ,
        )
        item.tags_description = self.tags_description
        return item

    def __str__(self):
        return self.name

    def __repr__(self):
        return u'%s (%s) %s' % (self.name, ', '.join(map(unicode,self.tags)), self.url)


# ------------------------------------------------------------------------

class Tag(object):

    ILLEGAL_CHARACTERS = ',@#+:<>'

    # ',' is used to separate tags
    # '@' is used to denote tag id
    # '#' is used to denote comment
    # '<' reserve as operator for category description
    # '>' reserve as operator for category description
    # '+' reserve as operator for category description
    # ':' reserve as operator for category description
    #     e.g.
    #       SanFran+museum
    #       SanFran:museum
    #       SanFran>museum
    #
    # Note that we have O(n) algorithm with respect to the length of
    # ILLEGAL_CHARACTERS. It is only suppose to have a small number
    # of characters.

    @staticmethod
    def hasIllegalChar(s):
        for c in Tag.ILLEGAL_CHARACTERS:
            if c in s:
                return True
        return False

    @staticmethod
    def cleanIllegalChar(s, dont_clean=''):
        """
        Alternatively replace illegal characters with '?' rather than
        rejecting the input.
        """
        for c in Tag.ILLEGAL_CHARACTERS:
            if c in dont_clean:
                continue
            if c in s:
                s = s.replace(c,'.')
        return s

    def __init__(self,
        id          =-1,
        timestamp   ='',
        version     =0,
        name        ='',
        description ='',
        flags       ='',
        ):

        if not name:
            raise ValueError('Tag name required')

        self.id         = id
        self.timestamp  = timestamp
        self.version    = version
        self.name       = name
        self.description= description
        self.flags      = flags

        self.num_item   = 0

    def __copy__(self):
        tag = Tag(
            id          = self.id           ,
            timestamp   = self.timestamp    ,
            version     = self.version      ,
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
        # root of tree of tags
        # note: the root is always an pseudo empty node (usually not visible)
        self.root = graph.Node(None,[])
        self.description = ''

    def getUncategorized(self):
        """
        Return list of uncategorized tags in name order.
        """
        tags = sets.Set(self.wlib.tags)
        categorized_tags = [node.data for node, _ in self.root.dfs() if node.data]
        uncategorized = tags.difference(categorized_tags)
        return sortTags(uncategorized)


    def getDescription(self):
        return self.description


    def setDescription(self, description):
        self.description = Tag.cleanIllegalChar(description)

        # TODO: Note that setDescription() is called by renameTag() and
        # deleteTag() for each tag. It does compile() and write to disk.
        # This would be inefficient if we are editing a series of tags.
        # However, so far only edit and delete of individual tag is
        # used [2005-12-07].
        # TODO: clean up
        self._compile(self.description)
        self.wlib.store.writeNameValue('category_description', self.description)


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


    def _compile(self, description=None):
        """
        Build root from category_description
        """
        # try a description parameter instead of using self.description because
        # sometimes we need to call _compile() before changing the description
        if description == None:
            description = self.getDescription()

        self.root = graph.parse_text_tree(description)

        # walk the parsed tree
        # - create new tags
        # - convert string to tag
        for node, p in self.root.dfs():
            name = node.data
            tag = self.wlib.tags.getByName(name)
            if (not tag) and name:
                tag = Tag(name=name)
                tag = self.wlib.store.writeTag(tag)
                log.debug(u'Add tag from category: %s' % unicode(tag))
            node.data = tag


    # TODO: _countTag is only used in weblibTagCategorize?
    # TOOD: cleanup?
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
        self.version = ''
        self.date = ''

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


#    # TODO: this is not used right now
#    def updateWebPage(self, item):
#        """
#        The item updated can be new or existing.
#        """
#        print >>sys.stderr, '## index %s' % item.name
#        return
#        self._delete_index(item)
#        scontent = self._get_snapshot_content(item)
#        print >>sys.stderr, '## ss [%s]' % scontent[:50]
#        content = '\n'.join([
#            item.name,
#            item.description,
#            scontent,
#        ])
#
#        self.index_writer.addDocument(
#            item.id,
#            dict(
#                uri=item.url,
#                date='',
#                ),
#            content,
#        )    # todo date


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
    # Tag methods

    def getDefaultTag(self):
        d = cfg.get('weblib.tag.default', TAG_DEFAULT)
        if not d:
            return None
        tag = self.tags.getByName(d)
        if tag:
            return tag
        # default tag is not previous used; or user has chosen a new default?
        return self.store.writeTag(Tag(name=d))


    def tag_rename(self, tag, newName):
        log.debug(u'tag_rename tag count=%s tag=%s newName=%s', len(self.tags), unicode(tag), newName)
        oldName = tag.name
        newTag = tag.__copy__()
        newTag.name = newName
        self.store.writeTag(newTag)
        self.category.renameTag(oldName, newName)


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


    # 2006-01-06 Need to think twice about this. Import has 2 possibilities, use new or use existing.

#    def draftWebPage(self, page_in):
#        """
#        Draft a WebPage by taking input from page_in and looking up
#        existing webpage by the same URL.
#
#        The fields of page_in are interpreted by:
#
#        id              - ignored, either generates a new id or lookup an existing id
#        url             - used to match existing item in the wlib
#        name            - proposed name (overridden by existing item)
#        description     - proposed description (overridden by existing item)
#        created         - if None, substitute with today or the value of the existing item
#        modified        - if None, substitute with today
#        tags_description- if not None, used to build the tags list; create any new tags
#
#        @return - a draft WebPage. If its id is not -1, it matches an existing item.
#        """
#        today = datetime.date.today().isoformat()
#
#        import query_wlib
#        matches = query_wlib.find_url(self, page_in.url)
#        if matches:
#            existing = matches[0]
#                self.oldItem = matches[0]
#                item = existing.__copy__()
#                # however override with possibly new title and description
#                item.name        = req.param('title')
#                item.description = req.param('description')
#                # actually the item is not very important because we
#                # are going to redirect the request to the proper rid.
#
#        else:
#            page_in.id = -1
#            if page_in.created is None:
#                page_in.created = today
#            if page_in.modified is None:
#                page_in.modified = today


    def putWebPage(self, page):
        """
        Put a webpage into the weblib. This is a higher level function
        (compares to inserting a raw record). It updates some fields
        according to the list below:

        id              - ignored, either generates a new id or lookup an existing id
        url             - used to match existing item in the wlib
        modified        - if None, substitute with today
        created         - if None, substitute with today or the value of the existing item
        tags_description- if not None, used to build the tags list; create any new tags

        @return - (isNew, newPage object)
        """
        today = datetime.date.today().isoformat()

        import query_wlib
        matches = query_wlib.find_url(self, page.url)
        if matches:
            old = matches[0]
            page.id = old.id
            if page.created is None:
                page.created = old.created
        else:
            page.id = -1
            if page.created is None:
                page.created = today

        if page.modified is None:
            page.modified = today

        if page.tags_description is not None:
            # caller should have checked for illegal characters
            # if you don't, they will be cleaned here
            page.tags_description = Tag.cleanIllegalChar(page.tags_description,',')
            page.tags = makeTags(self.store, page.tags_description)
            page.tags_description = None

        if page.id < 0:
            log.info('Adding WebPage: %s' % unicode(page))
        else:
            log.info('Updating WebPage: %s' % unicode(page))
        newPage = self.store.writeWebPage(page)

        return bool(matches), newPage


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


    # ------------------------------------------------------------------------

    def __repr__(self):
        return 'WebLibraray date=%s version=%s #tags=%s #pages=%s' % (
            self.date,
            self.version,
            len(self.tags),
            len(self.webpages),
            )


# ----------------------------------------------------------------------

def parseTag(wlib, nameOrId):
    """ Parse tag names or tag id. Return tag or None. """
    # tag id in the format of @ddd?
    if nameOrId.startswith('@') and nameOrId[1:].isdigit():
        id = int(nameOrId[1:])
        return wlib.tags.getById(id)
    else:
        return wlib.tags.getByName(nameOrId)


def parseTags(wlib, tags_description):
    """
    Parse comma separated tags_description.
    @return: list of tags and list of unknown tag names.
    """
    tags = []
    tags_set = set()
    unknown = []
    unknown_set = set()
    for name in tags_description.split(','):
        name = name.strip()
        if not name:
            continue
        tag = parseTag(wlib, name)
        if tag:
            if tag not in tags_set:
                tags.append(tag)
                tags_set.add(tag)
        else:
            lname = name.lower()
            if lname not in unknown_set:
                unknown.append(name)
                unknown_set.add(lname)

    return tags, unknown


def makeTags(store, tags_description):
    """
    Parse comma separated tags_description.
    Create tags if not already in repository.
    @return: list of tags
    """

    # Sanity check. UI should have block this already?
    d1 = tags_description.replace(',',' ')  # ',' is valid separator
    if Tag.hasIllegalChar(d1):
        raise ValueError('Illegal characters for tags in "%s"' % tags_description)

    tags, unknown = parseTags(store.wlib, tags_description)
    for name in unknown:
        newTag = Tag(name=name)
        tag = store.writeTag(newTag)
        log.debug(u'Added tag: %s' % unicode(tag))

    if unknown:
        # parseTags() again to get a list of all Tags (in input order)
        tags, unknown = parseTags(store.wlib, tags_description)
        assert not unknown

    return tags


def sortTags(tags):
    """ sort tags by name in alphabetical order """
    lst = [(tag.name.lower(), tag) for tag in tags]
    return [pair[1] for pair in sorted(lst)]


#-----------------------------------------------------------------------

def main(argv):
    pass

if __name__ =='__main__':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout,'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr,'replace')
    main(sys.argv)
