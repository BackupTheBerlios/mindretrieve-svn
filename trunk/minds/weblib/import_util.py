"""
Import Netscape bookmark.
"""

import codecs
import datetime
import logging
import StringIO
import sys
import urllib

from minds.config import cfg
from minds import app_httpserver
from minds import weblib
from minds.weblib import query_wlib
from minds.weblib import store
from minds.util import fileutil

log = logging.getLogger('wlib.imprt')


def _ctime_str_2_iso8601(s):
    if not s: return ''
    try:
        dt = datetime.date.fromtimestamp(int(s))
    except ValueError:
        return ''
    return dt.isoformat()


class Folder(object):
    def __init__(self, name):
        self.name = name
        self.children = []

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



def build_category(folder, cat_buf, path=None):
    """ walk the folder tree recursively and build the category description """
    if path == None:
        path = []

    cat_buf.write('  ' * (len(path)-1))   # negative ok
    cat_buf.write(folder.name)
    cat_buf.write('\n')

    path.append(folder)
    tags = ','.join([f.name for f in path])
    for item in folder.children:
        if isinstance(item, Folder):
            build_category(item, cat_buf, path)
        else:
            item.tags = tags
            _add_item(item)
    path.pop()


def _add_item(item):
    # if it match existing item, make it an update
    # otherwise the CGI would ask us to redirect, which we try to avoid
    items = query_wlib.find_url(store.getWeblib(), item.url)
    if items:
        id = items[0].id
    else:
        id = '_'

    # Add the item via CGI. Probably not the fastest.
    # But there is less code to write and the API will become official
    url = '/weblib/%s?' % id + urllib.urlencode({
            'method':      'PUT',
            'title':       item.name.encode('utf-8'),
            'url':         item.url.encode('utf-8'),
            'description': item.description.encode('utf-8'),
            'tags':        item.tags.encode('utf-8'),
            'modified':    item.modified,
            'lastused':    item.created,            #######HACK HACK HACK
            'create_tags': '1',
        })

    # faster via app_httpserver than socket?
    buf = fileutil.aStringIO()
    app_httpserver.handlePath(url, buf)

    # check status
    buf.seek(0)
    status = buf.readline()
    if ' 200 ' not in status and ' 302 ' not in status:
        log.warn('Unable to add %s: %s' % (item.name, status))

    return


def import_tree(root_folder):
    cat_buf = StringIO.StringIO()
    cat_buf.write('\n')
#    cat_buf.write('#------------------------------------------------------------------------')
#    cat_buf.write('Netscape-Imported-Category-%s\n' % str(datetime.date.today()))

    build_category(root_folder, cat_buf)

    # append cat_buf to category description
    wlib = store.getWeblib()
    new_cat = wlib.category.getDescription() + cat_buf.getvalue()
    wlib.category.setDescription(new_cat)


def main(argv):
    pathname = argv[1]
    import_bookmark(pathname)


if __name__ =='__main__':
    sys.stdout = codecs.getwriter('utf8')(sys.stdout,'replace')
    sys.stderr = codecs.getwriter('utf8')(sys.stderr,'replace')
    main(sys.argv)
