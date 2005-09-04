""" __init__.py [options] [args]
    -q:     query
"""

# TODO: how do I make sure WebPage fields is the right type? e.g. id is int.
# date fields: modified, cached, accessed

import codecs
import datetime
import random
import sets
import string
import sys
import urlparse

from minds.config import cfg
from minds.util import dsv
import util


TAG_DEFAULT = 'inbox'

class WebPage(object):

    def __init__(self, id=-1,
        name        ='',
        url         ='',
        description ='',
        tagIds      =[],
        relatedIds  =[],
        modified    ='',
        lastused    ='',
        cached      ='',
        archived    ='',
        flags       ='',
    ):
        # put all parameter values as instance variable
        self.__dict__.update(locals())
        del self.self
        self.tags = []
        self.related = []

    def __copy__(self):
        item = WebPage(
            id          = self.id           ,
            name        = self.name         ,
            url         = self.url          ,
            description = self.description  ,
            tagIds      = self.tagIds[:]  ,
            relatedIds  = self.relatedIds[:],
            modified    = self.modified     ,
            lastused    = self.lastused     ,
            cached      = self.cached       ,
            archived    = self.archived     ,
            flags       = self.flags        ,
        )    
        item.tags  = self.tags[:]
        item.related = self.related[:]   
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
        self.webpages = util.IdList()
        self.tags = util.IdNameList()
        # todo: should implement a rfc822.Message style case-insensitive dictionary
        self.headers_list = []


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
        self.categorize()
        return tag
        
 
    def updateWebPage(self, updatedItem):
        pass
        
                       
    def categorize(self):
##        """ call this when finished loading """
##        
##        # set item.tags from tagIds
##        for item in self.webpages:
##            tags = [self.tags.getById(id) for id in item.tagIds]
##            item.tags = filter(None, tags)
##            # remove tagIds to avoid duplicated data?            
        #TODO: clean this
        import category
        self.categories = category.buildCategory(self)
        

# ----------------------------------------------------------------------
        
def parseTags(wlib, tag_names):
    """ Parse comma separated tag names.
        @return: list of tags and list of unknown tag names.
    """
    tags = []
    unknown = []
    for name in tag_names.split(','):
        name = name.strip()
        if not name:
            continue
        tag = wlib.getTag(name)
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

def query(wlib, querytxt, tags):
    """ @return: 
            cat_list, - tuple of tags -> list of items, 
            related, 
            most_visited
    """
    querywords = querytxt.lower().split()
    if not querywords and not tags:
        return queryMain(wlib)
        
    # use querytxt to match additional tags
    tags_set = sets.Set(tags)
    query_tags_set = sets.Set((tag for tag in wlib.tags if tag.name.lower() in querywords))
        
    print >>sys.stderr, 'querywords', querywords##
    print >>sys.stderr, 'query_tags_set', query_tags_set
    print >>sys.stderr, 'tags_set', tags
    
    most_visited = None
    cat_list = {}
    related = sets.Set()
    
    ## TODO: logic is complicated, need some refactoring
    # short circuit behavior is hard to archieve.
    # blank querytxt and tags change the meaning.
    for item in wlib.webpages:

        # first line filtering by tag
        if tags:
            _td = tags_set.difference(item.tags)
            if bool(_td):
                continue

        if query_tags_set:
            _qti = query_tags_set.intersection(item.tags)
            qt_matched = bool(_qti)
        else:    
            qt_matched = False
                
        netloc = urlparse.urlparse(item.url)[1].lower()
        if querywords:
            q_matched = True
            for w in querywords:
                if (w not in item.name.lower()) and (w not in netloc):
                    q_matched = False
                    break
            if not q_matched and not qt_matched:
                continue
        
            # most visited only activates with a querytxt        
            if q_matched:
                if not most_visited or \
                    item.lastused > most_visited.lastused:
                    most_visited = item
        else:
            q_matched = False
                
        if querywords and not (qt_matched or q_matched):
            continue
            
        cat = util.diff(item.tags, tags)
        cat2bookmark = cat_list.setdefault(tuple(cat),[])
        cat2bookmark.append(item)
        related.union_update(item.tags)
    
    if tags: ##hack
        related = analyzeRelated(tags[0],related)
        print >>sys.stderr, related
    else:
        related = [(t.rel.num_item, t.rel) for t in related]
        related = [related,[],[]]
        
        
    return cat_list, tuple(related), most_visited 

##refactor
def analyzeRelated(tag,related):
    parents, children, others = [],[],[]
    for count, rel in tag.rel.related:
        if count == tag.rel.num_item:
            parents.append((rel.torder, rel))
        elif count == rel.num_item:
            children.append((rel.torder, rel))
        else:
            pe = 100 * count / tag.rel.num_item
            ce = 100 * count / rel.num_item
            x =  (pe+ce,pe,ce)
            others.append((x, rel))
    parents.sort()
    children.sort()
    others.sort(reverse=True)        

    return (parents, children, others)


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

def doQuery(wlib, querytxt, tags):
    tags,unknown = parseTags(wlib, tags)
    if unknown:
        print 'Ignore unknown tags', unknown

    cat_list, related, most_visited = query(wlib, querytxt, tags)

    pprint(tags)
    listCatList(wlib,cat_list)
    pprint(sortTags(related))
    print 'Most visited:', most_visited


def listCatList(wlib,lst):
    for key, value in sorted(lst.items()):
        sys.stdout.write('\n' + u','.join(map(unicode, key)) + '\n')
        for item in value:
            tags = [tag.name for tag in item.tags]
            related = [tag.name for tag in item.related]
            print '  %s (%s) (%s)' % (unicode(item), ','.join(tags), ','.join(related))


def show(wlib):
    for item in wlib.webpages:
        tags = [tag.name for tag in item.tags]
        related = [tag.name for tag in item.related]
        print '%s (%s) (%s)' % (item.name, ','.join(tags), ','.join(related))


def main(argv):

    import store

    wlib = store.load()

    if len(argv) <= 1:
        show(wlib)
        sys.exit(0)
        
    querytxt = ''    
    if argv[1] == '-q':
        querytxt = argv[2]
        del argv[:2]
        
    tags = len(argv) > 1 and argv[1] or ''
        
    doQuery(wlib, querytxt, tags)


if __name__ == '__main__':
    sys.stdout = codecs.getwriter('utf8')(sys.stdout,'replace')
    main(sys.argv)