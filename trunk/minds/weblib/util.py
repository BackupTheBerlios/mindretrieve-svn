
def diff(a,b):
    """ return a-b """
    d = []
    for k in a:
        if k not in b:
            d.append(k)
    return d



#-----------------------------------------------------------------------
# Id keyed list

class IdList(object):
    """ A container keyed by id """

    def __init__(self):
        self._lastId = 0
        self._lst = []
        self._id2item = {}

    def append(self, item):
        if item.id < 0:
            # generate new id
            self._lastId += 1
            item.id = self._lastId

        elif item.id > self._lastId:
            # id supplied, maintain self._lastId
            self._lastId = item.id

        if self._id2item.has_key(item.id):
            raise KeyError('Duplicated %s id "%s"' % (unicode(item), item.id))

        self._lst.append(item)
        self._id2item[item.id] = item

    def getById(self, id):
        """ @return item or None if not found """
        return self._id2item.get(id, None)

    def remove(self, item):
        """ raise KeyError if item is not in the list """
        try:
            self._lst.remove(item)
        except ValueError, e:
            raise KeyError(e)     # make it an IndexError
        del self._id2item[item.id]

    def __len__(self):
        return len(self._lst)

    def __iter__(self):
        return iter(self._lst)


class IdNameList(IdList):
    """ A container keyed by id and name. """

    def __init__(self):
        super(IdNameList, self).__init__()
        self._name2item = {}

    def append(self, item):
        lname = item.name.lower()
        if not lname or self._name2item.has_key(lname):
            raise KeyError('Duplicated or invalid name "%s" tag %s' % (lname, unicode(item)))
        super(IdNameList, self).append(item)
        self._name2item[lname] = item

    def getByName(self, name):
        """
        @param name - would turn into lower case before lookup.
        @return item or None if not found
        """
        lname = name.lower()
        return self._name2item.get(lname, None)

    def remove(self, item):
        """ raise KeyError if item is not in the list """
        del self._name2item[item.name.lower()]
        super(IdNameList, self).remove(item)

    def rename(self, item, newName):
        # rename need to takes care of self._name2item
        lNewName = newName.lower()
        if not lNewName:
            raise KeyError('Invalid name "%s"' % lNewName)
        test_item = self.getByName(lNewName)
        if test_item and test_item != item:
            raise KeyError('Duplicated name "%s", fail to rename %s' % (lNewName, unicode(item)))
        try:
            lname = item.name.lower()
            del self._name2item[lname]
        except ValueError:
            pass # should not happen
        item.name = newName
        self._name2item[lNewName] = item


