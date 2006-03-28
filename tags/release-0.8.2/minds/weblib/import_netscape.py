"""
Import Netscape bookmark.
"""

import codecs
import logging
import sys
import urllib

from minds.config import cfg
from minds import app_httpserver
from minds import weblib
from minds.weblib import import_util
from minds.weblib import query_wlib
from minds.weblib import store
from minds.util import html_pull_parser
from minds.util.html_pull_parser import DATA, TAG, ENDTAG, COMMENT

log = logging.getLogger('imp.nscape')


class PushBackIterator(object):
    """ Iterator that supports push back of 1 item """
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


def _get_attr(name_value_pair, attr, default=None):
    """ find value corresponding to attr among list of (name,value) """
    for n,v in name_value_pair:
        if n == attr:
            return v
    return default


def _join_text(lst):
    return ''.join(lst).strip()


def parseFile(rstream):
    # HACK: can we assume Netscape file is UTF-8 encoded?
    reader = codecs.getreader('utf-8')(rstream,'replace')

    tokens = html_pull_parser.generate_tokens3(reader)
    tokens = PushBackIterator(tokens)

    top_folder = import_util.Folder('')
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
                # this is a corrupted case, no preceding <dt>.
                # damage control: parse the <dl> and then drop it.
                parseList(tokens, folder)

        elif kind == TAG and data == 'dt':
            item = parseItem(tokens)
            folder.children.append(item)
            if isinstance(item,import_util.Folder):
                last_subfolder = item


def parseItem(tokens):
    """
    <dt>

    Terminate by <dt>, </dt>, <dl>, </dl> or EOF.
    Push back if terminated by tags.

    @return
        Bookmark if it has <a>;
        Folder otherwise
    """
    title = ''
    url = ''
    text = []
    dd_description = ''
    has_a = False
    for kind, data, attrs in tokens:
        if kind == DATA:
            text.append(data)
        elif kind == TAG and data == 'a':
            title, url, created, modified = parseLink(tokens, attrs)
            has_a = True
        elif kind == TAG and data == 'dd':
            dd_description = parseDescription(tokens)
        elif data in ('dl', 'dt'):
            # malformed!
            tokens.push_back((kind,data,attrs))
            break
        else:
            pass    # ignore others
    dt_text = _join_text(text)

    # it is either a Folder or Bookmark
    if has_a:
        return import_util.Bookmark(title, url, dd_description, created, modified)
    else:
        return import_util.Folder(dt_text)


def parseLink(tokens, attrs):
    # <a>
    url           = _get_attr(attrs, 'href')
    last_modified = _get_attr(attrs, 'last_modified')
    add_date      = _get_attr(attrs, 'add_date')

    last_modified = import_util._ctime_str_2_iso8601(last_modified)
    add_date      = import_util._ctime_str_2_iso8601(add_date)

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
    return _join_text(title), url, add_date, last_modified


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


def import_bookmark(fp):
    folder = parseFile(fp)
    return import_util.import_tree(folder)


def main(argv):
    pathname = argv[1]
    fp = file(pathname,'rb')
    import_bookmark(fp)


if __name__ =='__main__':
    sys.stdout = codecs.getwriter('utf8')(sys.stdout,'replace')
    sys.stderr = codecs.getwriter('utf8')(sys.stderr,'replace')
    main(sys.argv)
