"""
Usage: import_delicious.py filename | (username password)

"""
import base64
import codecs
import datetime
import logging
import sys
import urllib2
import xml.sax
import xml.sax.handler

from minds.config import cfg
from minds import weblib
from minds.weblib import import_util

log = logging.getLogger('imp.del.i.')


# del.icio.us use this as filler for webpage with no tags
TAG_FILLER = 'system:unfiled'


POSTS_URL = 'http://del.icio.us/api/posts/all'

def parse(fp):
    parser = xml.sax.make_parser()
    handler = DeliciousHandler()
    parser.setFeature(xml.sax.handler.feature_namespaces, 1)
    parser.setContentHandler(handler)
    try:
        parser.parse(fp)
    except xml.sax.SAXParseException, e:
        log.warn('Error parsing delicious import: %s' % e)
        return None
    return handler.bookmarks


class DeliciousHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        xml.sax.handler.ContentHandler.__init__(self)
        self.bookmarks = []

    def startElementNS(self, name, qname, attrs):
        uri,localname = name
        if localname != 'post':
            return

        # <post> tag
        url         = attrs.get((None,'href'),'')
        name        = attrs.get((None,'description'),'')
        description = attrs.get((None,'extended'),'')
        created     = attrs.get((None,'time'), '')
        tags        = attrs.get((None,'tag'), '')

        created = created[:10]          # ISO8601 date
        if tags == TAG_FILLER:
            tags = ''
        tags = ','.join(tags.split())   # ' ' --> ','
        # TODO: clean illegal characters

        page = import_util.Bookmark(
            name,
            url         = url,
            description = description,
            created     = created,
            )
        page.tags = tags
        self.bookmarks.append(page)


def fetch_delicious(url, user, password):
    request = urllib2.Request(url)
    auth = base64.encodestring('%s:%s' % (user, password)).rstrip()
    request.add_header("Authorization", "Basic %s" % auth)
    fp = urllib2.urlopen(request)
    return fp


def import_bookmark(fp):
    bookmarks = parse(fp)
    if not bookmarks:
        return 0, 0
    return import_util.import_bookmarks(bookmarks)



def main(argv):
    if len(argv) <= 1:
        print __doc__
        sys.exit(-1)
    elif len(argv) == 2:
        pathname = argv[1]
        fp = file(pathname,'rb')
    else:
        fp = fetch_delicious(POSTS_URL, argv[1],argv[2])
    import_bookmark(fp)


if __name__ =='__main__':
    sys.stdout = codecs.getwriter('utf8')(sys.stdout,'replace')
    sys.stderr = codecs.getwriter('utf8')(sys.stderr,'replace')
    main(sys.argv)
