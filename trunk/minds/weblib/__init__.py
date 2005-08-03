""" __init__.py [cmd] [args]
    query:  labels
    cats:   labels
"""

import codecs
import datetime
import sets
import sys

import util
from minds.util import dsv


# TODO: how do I make sure WebPage fields is the right type? e.g. id is int.

# date fields: modified, cached, accessed
# field remove commented?

class WebPage(object):

    def __init__(self, id=-1,
        name        ='',
        url         ='',
        description ='',
        labelIds    =[],
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
        self.labels = []
        self.related = []

    def __copy__(self):
        item = WebPage(
            id          = self.id           ,
            name        = self.name         ,
            url         = self.url          ,
            description = self.description  ,
            labelIds    = self.labelIds[:]  ,
            relatedIds  = self.relatedIds[:],
            modified    = self.modified     ,
            lastused    = self.lastused     ,
            cached      = self.cached       ,
            archived    = self.archived     ,
            flags       = self.flags        ,
        )    
        item.labels  = self.labels[:]
        item.related = self.related[:]   
        return item
        
    def __str__(self):
        return self.name

    def __repr__(self):
        return u'%s (%s) %s' % (self.name, ', '.join(map(unicode,self.labels)), self.url)


class Label(object):

    def __init__(self, id=-1, name=''):
        
        if not name:
            raise RuntimeError('Label name required')
            
        self.id         = id
        self.name       = name

        self.isTag      = []    # isTag is intersection of all labels for all items
        self.related    = {}    # relatedLabel -> count, relatedLabels is union of all label for all items
                                # Then inferRelation() would make it a list of tuples???
        self.num_item   = 0

    def __str__(self):
        return self.name

    def __repr__(self):
        return unicode(self)


class WebLibrary(object):

    def __init__(self):
        self.webpages = util.IdList()
        self.labels = util.IdNameList()
#        self._lastId = 0
#        self.webpages = []
#        self.id2entry = {}
#        self.name2label = {}    # lower name -> Tag


    def addWebPage(self, entry):
        self.webpages.append(entry)


    def addLabel(self, entry):
        self.labels.append(entry)


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


    def getLabel(self, name):
        return self.labels.getByName(name)


    def fix(self):
        """ call this when finished loading """
        for item in self.labels:
            item.related = {}   # HACK HACK

        for item in self.webpages:
            setTags(item, self)
            
        for item in self.labels:
            inferRelation(item)



def parseLabels(wlib, label_names):
    """ Parse comma separated tag names.
        @return: list of labels and list of unknown tag names.
    """
    labels = []
    unknown = []
    for name in label_names.split(','):
        name = name.strip()
        if not name:
            continue    
        label = wlib.getLabel(name)
        if label:
            labels.append(label)
        else:
            unknown.append(name)
    labels.sort()        
    return labels, unknown


def sortLabels(labels):
    lst = [(label.name.lower(), label) for label in labels]
    lst.sort()
    return [lbl for _,lbl in lst]
    
    
wlib = None

def getMainBm():
    global wlib
    if not wlib:
        import store
        wlib = store.load()
    return wlib



########################################################################
# Query

# experimental
def setTags(item, wlib):
    labels = [wlib.labels.getById(id) for id in item.labelIds]
    labels = filter(None, labels)
    labels.sort()
    related = [wlib.labels.getById(id) for id in item.relatedIds]
    related = filter(None, related)
    related.sort()
    # TODO: remove labelIds and relatedIds to avoid duplicated data?
    # TODO: don't sort to retain order?
    item.labels = labels
    item.related = related
    for folder in labels:
        folder.related = {}
        folder.num_item += 1
        for relatedTag in labels:
            if relatedTag == folder: 
                continue
            count = folder.related.setdefault(relatedTag,0)
            folder.related[relatedTag] = count+1

#experimental
def inferRelation(self):
    self.related = [(count,folder) for folder, count in self.related.items()]
    self.related.sort(reverse=True)
    self.isTag = [tag for count, tag in self.related if count == self.num_item]


def query(wlib, labels):
    """ @return: cat_list, related
            cat_list: tuple of labels -> list of items,
    """
    cat_list = {}
    related = sets.Set()
    for item in wlib.webpages:
        if util.diff(labels, item.labels):
            continue
        cat = util.diff(item.labels, labels)
        cat2bookmark = cat_list.setdefault(tuple(cat),[])
        cat2bookmark.append(item)
        related.union_update(item.labels)
    return cat_list, tuple(related)


def queryMain(wlib):
    """ @return: cat_list, related where
            cat_list: tuple of labels -> list of items,
    """
    items = [item for item in wlib.webpages if not item.labels]
    labels = [l for l in wlib.labels]
    return {tuple(): items}, labels
        
    

# ----------------------------------------------------------------------
# Command line

from pprint import pprint

def doQuery(wlib, tags):
    labels,unknown = parseLabels(wlib, tags)
    if unknown:
        print 'Ignore unknown labels', unknown

    cat_list, related = query(wlib, labels)

    pprint(labels)
    listCatList(wlib,cat_list)
    pprint(sortLabels(related))


def listCatList(wlib,lst):
    for key, value in sorted(lst.items()):
        sys.stdout.write('\n' + u','.join(map(unicode, key)) + '\n')
        for item in value:
            tags = [label.name for label in item.labels]
            related = [label.name for label in item.related]
            print '  %s (%s) (%s)' % (unicode(item), ','.join(tags), ','.join(related))


def show(wlib):
    for item in wlib.webpages:
        tags = [label.name for label in item.labels]
        related = [label.name for label in item.related]
        print '%s (%s) (%s)' % (item.name, ','.join(tags), ','.join(related))


def main(argv):

    import store

    wlib = store.load()

    if len(argv) <= 1:
        show(wlib)
        sys.exit(0)
        
    cmd = argv[1]    
    args = ''
    if len(argv) > 2:
        args = argv[2]
        
    doQuery(wlib, args)


if __name__ == '__main__':
    sys.stdout = codecs.getwriter('utf8')(sys.stdout,'replace')
    main(sys.argv)