"""
Import Netscape bookmark.
"""

import datetime
import codecs
import logging
import StringIO
import sys
import urllib

from minds.config import cfg
from minds import app_httpserver
from minds import weblib
from minds.weblib import query_wlib
from minds.weblib import store
from minds.util import html_pull_parser
from minds.util import fileutil

log = logging.getLogger('wlib.nscpe')



DATA, TAG, ENDTAG, COMMENT = (\
    html_pull_parser.DATA,
    html_pull_parser.TAG,
    html_pull_parser.ENDTAG,
    html_pull_parser.COMMENT,
    )


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
    def __init__(self, name, url='', description=''):
        self.name = name
        self.url = url
        self.description = description
        self.tags = ''

    def __repr__(self):
        return u'%s (%s)' % (self.name, self.url)


class PushBackIterator(object):
    """ Iterator that supports of 1 item """
    def __init__(self, it):
        self.it = it
        self.backItem = None

    def __iter__(self):
        return self

    def next(self):
        if self.backItem:
            r = self.backItem
            self.backItem = None
            return r
        return self.it.next()

    def push_back(self, item):
        assert item
        self.backItem = item


def _get_attr(name_value_pair, attr):
    for n,v in name_value_pair:
        if n == attr:
            return v
    return None


def _join_text(lst):
    return ''.join(lst).strip()


def main(argv):
    folder = parseFile(argv[1])
    cat_buf = StringIO.StringIO()
    cat_buf.write('\n#------------------------------------------------------------------------')
    cat_buf.write('Netscape-Imported-Category-%s\n' % str(datetime.date.today()))
    build_category(folder, cat_buf)
    wlib = store.getWeblib()
    new_cat = wlib.category.getDescription() + cat_buf.getvalue()
    wlib.category.setDescription(new_cat)


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


def parseFile(pathname):
    fp = file(pathname,'rb')

    # HACK: can we assume Netscape file is UTF-8 encoded?
    reader = codecs.getreader('utf-8')(fp,'replace')

    tokens = html_pull_parser.generate_tokens3(reader)
    tokens = PushBackIterator(tokens)

    top_folder = Folder('')
    for kind,data,_ in tokens:
        if kind == TAG and data == 'dl':
            parseList(tokens, top_folder)
            break

    return top_folder


def parseList(tokens, folder):
    """
    <dl>

    Keep reading until corresponding </dl>.
    Return the list of items parsed.
    """
    last_subfolder = None
    for kind, data, _ in tokens:
        if kind == ENDTAG and data == 'dl':
            break
        elif kind == TAG and data == 'dl':
            if last_subfolder:
                # this is the normal case, <dl> preceded by a <dt> of folder name
                parseList(tokens, last_subfolder)
                last_subfolder = None
            else:
                # this is corrupted case. Just do damage control
                parseList(tokens, folder)
        elif kind == TAG and data == 'dt':
            item = parseItem(tokens)
            folder.children.append(item)
            if isinstance(item,Folder):
                last_subfolder = item


def parseItem(tokens):
    """
    <dt>

    Terminate by <dt>, </dt>, <dl>, </dl> or EOF.
    Push back if terminated by tags.
    """
    title = None
    url = None
    description = []
    dd_description = None
    for kind, data, attrs in tokens:
        if kind == DATA:
            description.append(data)
        elif kind == TAG and data == 'a':
            title, url = parseLink(tokens, attrs)
        elif kind == TAG and data == 'dd':
            dd_description = parseDescription(tokens)
        elif data in ('dl', 'dt'):
            # malformed!
            tokens.push_back((kind,data,attrs))
            break

    description = _join_text(description)
    description = dd_description or description

    # it is either a Folder or Bookmark
    if title != None:
        return Bookmark(title, url, description)
    else:
        return Folder(description)


def parseLink(tokens, attrs):
    # <a>
    url = _get_attr(attrs, 'href')
    title = []
    for kind, data, attrs in tokens:
        if kind == DATA:
            title.append(data)
        elif kind == ENDTAG and data == 'a':
            break
        elif data in ('dl','dt', 'dd'):
            # malformed!
            tokens.push_back((kind,data,attrs))
            break
    return _join_text(title), url


def parseDescription(tokens):
    # <dd>
    description = []
    for kind, data, attrs in tokens:
        if kind == DATA:
            description.append(data)
        elif kind == ENDTAG and data == 'dd':
            break
        elif data in ('dl','dt'):
            # malformed!
            tokens.push_back((kind,data,attrs))
            break
    return _join_text(description)


if __name__ =='__main__':
    sys.stdout = codecs.getwriter('utf8')(sys.stdout,'replace')
    sys.stderr = codecs.getwriter('utf8')(sys.stderr,'replace')
    main(sys.argv)
