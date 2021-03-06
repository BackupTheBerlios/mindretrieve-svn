
def diff(a,b):
    """ return a-b """
    d = []
    for k in a:
        if k not in b:
            d.append(k)
    return d


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



#-----------------------------------------------------------------------
# Id keyed list

class IdList(object):
    """ A container keyed by id """

    def __init__(self):
        self._lastId = 0
        self._lst = []
        self._id2item = {}
        self.change_count = 0

    def acquireId(self):
        self._lastId += 1
        return self._lastId

    def append(self, item):
        if item.id < 0:
            item.id = self.acquireId()

        elif item.id > self._lastId:
            # id supplied, maintain self._lastId
            self._lastId = item.id

        if self._id2item.has_key(item.id):
            raise KeyError('Duplicated %s id "%s"' % (unicode(item), item.id))

        self._lst.append(item)
        self._id2item[item.id] = item
        self.change_count += 1


    def getById(self, id):
        """ @return item or None if not found """
        return self._id2item.get(id, None)

    def remove(self, item):
        """ raise KeyError if item is not in the list """
        try:
            self._lst.remove(item)
            self.change_count += 1
        except ValueError, e:
            raise KeyError(e)     # make it an IndexError
        del self._id2item[item.id]

    def __len__(self):
        return len(self._lst)

    def __iter__(self):
        return FailFastIterator(self)


class FailFastIterator(object):
    """
    Iterator of IdList. FailFastIterator raise an exception if
    the content of the container is changed during iteration.
    """

    def __init__(self, container):
        self.container = container
        self.init_count = container.change_count
        self.it = iter(container._lst)

    def next(self):
        if self.init_count != self.container.change_count:
            raise RuntimeError('Unable to iterate. Container has been modified')
        return self.it.next()



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

# 2005-11-25 Note:
# To rename a tag, call store.writeTag() with a new name.

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


# ------------------------------------------------------------------------
# URL utilities

def isFileURL(url):
    return url[:7].lower() == 'file://'


# base on nturl2path.py
def nt_url2pathname(url):
    r"""Convert a URL to a DOS path.

            ///C:/foo/bar/spam.foo

                    becomes

            C:\foo\bar\spam.foo
    """
    import string, urllib
    if not ':' in url:
        # No drive specifier, just convert slashes
        if url[:4] == '////':
            # path is something like ////host/path/on/remote/host
            # convert this to \\host\path\on\remote\host
            # (notice halving of slashes at the start of the path)
            url = url[2:]
        components = url.split('/')
        # make sure not to convert quoted slashes :-)
        return urllib.unquote('\\'.join(components))

    # HACK around
    # if you have '\' in your URL (only if it is first char?), it will affect the algorithm below
    url = url.replace('\\','/')

    comp = url.split(':',1)
    if len(comp) != 2 or comp[0][-1] not in string.ascii_letters:
        error = 'Bad URL: ' + url
        if isinstance(error,unicode):
            error = error.encode('UTF-8')
        error = error.encode('string_escape')
        raise SyntaxError(error)
    drive = comp[0][-1].upper()
    components = comp[1].split('/')
    path = drive + ':'
    for comp in components:
        if comp:
            path = path + '\\' + urllib.unquote(comp)
    return path


def nt_pathname2url(p):
    r"""Convert a DOS path name to a file url.

            C:\foo\bar\spam.foo

                    becomes

            ///C:/foo/bar/spam.foo
    """

    import urllib
    if not ':' in p:
        # No drive specifier, just convert slashes and quote the name
        if p[:2] == '\\\\':
        # path is something like \\host\path\on\remote\host
        # convert this to ////host/path/on/remote/host
        # (notice doubling of slashes at the start of the path)
            p = '\\\\' + p
        components = p.split('\\')
        return urllib.quote('/'.join(components))
    comp = p.split(':')
    if len(comp) != 2 or len(comp[0]) > 1:
        error = 'Bad path: ' + p
        if isinstance(error,unicode):
            error = error.encode('UTF-8')
        error = error.encode('string_escape')
        raise SyntaxError(error)

    drive = urllib.quote(comp[0].upper())
    components = comp[1].split('\\')
    path = '///' + drive + ':'
    for comp in components:
        if comp:
            path = path + '/' + urllib.quote(comp)
    return path
