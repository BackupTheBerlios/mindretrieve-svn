"""
Import bookmarks
def import_tree(root_folder):

"""

import datetime
import logging
import StringIO
import sys

from minds.config import cfg
from minds import weblib
from minds.weblib import store

log = logging.getLogger('wlib.imprt')


def _ctime_str_2_iso8601(s):
    if not s: return ''     # maybe None
    s = s.split('.',1)[0]   # drop fractional part
    if not s: return ''     # check again
    try:
        dt = datetime.date.fromtimestamp(int(s))
    except ValueError:
        return ''
    return dt.isoformat()


class Folder(object):
    def __init__(self, name, children=None):
        self.name = name
        if children:
            self.children = children
        else:
            self.children = []  # a new list, not the default parameter

    def __repr__(self):
        return u'%s(%s)' % (self.name, len(self.children))

    def dump(self, out, level=0):
        out.write('  ' * level)
        out.write(unicode(self))
        out.write('\n')
        for item in self.children:
            if isinstance(item, Folder):
                item.dump(out, level+1)
            else:
                out.write('  ' * (level+1))
                out.write(unicode(item))
                out.write('\n')


class Bookmark(object):
    def __init__(self, name, url='', description='', created='', modified=''):
        self.name        = name
        self.url         = url
        self.description = description
        self.created     = created
        self.modified    = modified
        self.tags        = ''

    def __repr__(self):
        return u'%s (%s)' % (self.name, self.url)


class WalkState(object):
    """ Keep the state of during traversal of folder tree """
    def __init__(self):
        self.update_count = 0
        self.add_count = 0
        self.cat_buf = StringIO.StringIO()
        self.cat_buf.write('\n')


def _build_category(folder, state, path=None):
    """ walk the folder tree recursively and build the category description """
    if path == None:
        path = []

    state.cat_buf.write('  ' * (len(path)-1))   # negative is ok
    state.cat_buf.write(folder.name)
    state.cat_buf.write('\n')

    wlib = store.getWeblib()

    path.append(folder)
    tags = ','.join([f.name for f in path])
    for item in folder.children:
        if isinstance(item, Folder):
            _build_category(item, state, path)
        else:
            page = weblib.WebPage(
                name        = item.name,
                url         = item.url,
                description = item.description,
                created     = item.created,
                modified    = item.modified,
                )
            page.tags_description = tags
            isNew, newPage = wlib.putWebPage(page)
            if isNew:
                state.update_count += 1
            else:
                state.add_count += 1
    path.pop()


def import_tree(root_folder):
    """
    Import hierarchical bookmark.

    root_folder is a Folder instance.
    It is the root to a collection of Folder and Bookmark objects.

    @return (added, updated)
    """
    state = WalkState()
    _build_category(root_folder, state)

    # append cat_buf to category description
    wlib = store.getWeblib()
    new_cat = wlib.category.getDescription() + state.cat_buf.getvalue()
    wlib.category.setDescription(new_cat)

    log.info('Import completed items added=%s updated=%s' % (state.add_count, state.update_count))
    return (state.add_count, state.update_count)


def import_bookmarks(bookmarks):
    """
    Import flat collection of bookmarks.
    bookmarks is a list of Bookmark.

    @return (added, updated)
    """
    wlib = store.getWeblib()
    update_count = 0
    add_count = 0
    for b in bookmarks:
        page = weblib.WebPage(
            name        = b.name,
            url         = b.url,
            description = b.description,
            created     = b.created,
            modified    = b.modified,
            )
        page.tags_description = b.tags
        isNew, newPage = wlib.putWebPage(page)
        if isNew:
            update_count += 1
        else:
            add_count += 1
    log.info('Import completed items added=%s updated=%s' % (add_count, update_count))
    return (add_count, update_count)
