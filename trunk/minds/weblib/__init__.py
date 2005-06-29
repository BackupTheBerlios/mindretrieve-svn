"""
"""

import codecs
from pprint import pprint
import sys

import util
from minds.util import dsv


# TODO: how do I make sure WebPage fields is the right type? e.g. id is int.

class WebPage(object):

    def __init__(self, id=-1,
        name        ='',
        url         ='',
        description ='',
        comment     ='',
        labelIds    =[],
        flags       ='',
        created     =None,
        modified    =None,
        archived    =None,
    ):
        self.id         = id
        self.name       = name
        self.url        = url
        self.description= description
        self.comment    = comment
        self.labelIds   = labelIds
        self.flags      = flags
        self.created    = created
        self.modified   = modified
        self.archived   = archived


    def __str__(self):
        return self.name


    def __repr__(self):
        return u'%s (%s) %s' % (self.name, ', '.join(map(str,self.labelIds)), self.url)



class Label(object):

    def __init__(self, id=-1, name=''):
        self.id         = id
        self.name       = name

        self.isTag      = []
        self.related    = {}
        self.num_item   = 0

    def __str__(self):
        return self.name

    def __repr__(self):
        return unicode(self)



class WebLibrary(object):

    def __init__(self):
        self.lastId = 0
        self.webpages = []
        self.labels = []
        self.id2entry = {}
        self.name2label = {}


    def addEntry(self, entry):

        if entry.id < 0:                # generate new id
            self.lastId += 1
            entry.id = self.lastId

        elif entry.id > self.lastId:    # id supplied, maintain self.lastId
            self.lastId = id

        if self.id2entry.has_key(entry.id):
            raise KeyError('Duplicated %s id "%s"' % (str(entry), entry.id))

        self.id2entry[entry.id] = entry


    def addWebPage(self, entry):
        self.addEntry(entry)
        self.webpages.append(entry)


    def addLabel(self, entry):

        low_name = entry.name.lower()
        if self.name2label.has_key(low_name):
            raise KeyError('Duplicated label %s' % low_name)

        self.addEntry(entry)
        self.labels.append(entry)
        self.name2label[low_name] = entry


    def getLabel(self, name):
        return self.name2label.get(name.lower(), None)



def parseLabels(wlib, label_names):
    """ Parse comma separated tag names.
        Return list of labels and list of unknown tag names.
    """
    labels = []
    unknown = []
    for name in label_names.split(','):
        name = name.strip()
        label = wlib.getLabel(name)
        if label:
            labels.append(label)
        else:
            unknown.append(name)

    return labels, unknown



wlib = None

#TODO: use config?

def getMainBm():
    global wlib
    if not wlib:
        import minds_bm
        fp = file('weblib.dat','rb')
        wlib = minds_bm.load(fp)
    return wlib



########################################################################
# Query

# experimental
def setTags(self, wlib):
    tags = [wlib.id2entry[id] for id in self.labelIds]
    for folder in tags:
        folder.num_item += 1
        for relatedTag in tags:
            if relatedTag == folder: continue
            count = folder.related.setdefault(relatedTag,0)
            folder.related[relatedTag] = count+1

#experimental
def inferRelation(self):
    self.related = [(count,folder) for folder, count in self.related.items()]
    self.related.sort(reverse=True)
    self.isTag = [tag for count, tag in self.related if count == self.num_item]



def query(wlib, labelIds):

    cat_list = {}

    for item in wlib.webpages:
        if isinstance(item, Label):
            continue
        if util.diff(labelIds, item.labelIds):
            continue
        cat = util.diff(item.labelIds, labelIds)
        cat2bookmark = cat_list.setdefault(tuple(cat),[])
        cat2bookmark.append(item)

    return cat_list



def listCatList(wlib,lst):
    for key, value in sorted(lst.items()):
        tags = [wlib.id2entry[id].name for id in key]
        print '\n' + u','.join(tags)
        for item in value:
            print '  ' + unicode(item)



def doQuery(wlib, tags):
    labels,unknown = parseLabels(wlib, tags)
    if unknown:
        print 'unknown labels', unknown
        return

    cat_list = query(wlib, [l.id for l in labels])

    pprint(labels)
    pprint(cat_list)
    return

    listCatList(wlib,cat_list)
    fp = file('x.out','wb')
    writer = codecs.getwriter('utf8')(fp,'replace')



def show(wlib):
    for item in wlib.webpages:
        tags = [wlib.id2entry[id].name for id in item.labelIds]
        print '%s (%s)' % (item.name, ','.join(tags))



def main(argv):

    import minds_bm

    fp = file(argv[1])
    wlib = minds_bm.load(fp)

    if len(argv) > 2:
        doQuery(wlib, argv[2])
    else:
        show(wlib)


if __name__ == '__main__':
    sys.stdout = codecs.getwriter('utf8')(sys.stdout,'replace')
    main(sys.argv)