"""Usage: ntfs_util.py (file_url | pathname) [title, comments, category]

Read/Write NTFS summary properties

Sample file URL:
  file:///C|/tmp/1.dat   <-->   c:\\tmp\\1.dat
"""

import os
import logging
import sys
#import urllib
import urlparse

import pythoncom
import pywintypes
import win32com.client

from minds.weblib import util
from toollib.path import path

log = logging.getLogger('win32.ntfs')


# 2005-12-20 TODO: make your own urllib.url2pathname
# 2005-12-20 TODO: test


def launch(file_url):
    scheme, netloc, url_path, _, _, _ = urlparse.urlparse(file_url)
    p = path(util.nt_url2pathname(url_path))
    log.debug('Launching file: %s' % p)
    os.startfile(p)


def makeWebPage(file_url):
    """
    Read the corresponding file's NTFS summary property and build a
    WebPage object. Fill with blank fields if can't read the
    properties.

    @returns - WebPage, tags (string)
    """
    scheme, netloc, url_path, _, _, _ = urlparse.urlparse(file_url)
    assert scheme == 'file'
    p = path(util.nt_url2pathname(url_path))

    props = None
    # _readProp() only work for read file
    # check this in advance to get friendlier error than the com_error
    if p.isfile():
        try:
            props = _readProp(p)
        except pywintypes.com_error, e:
            # file locked?
            log.exception('Unable to read NTFS property: %s' % p)

    from minds import weblib
    if not props:
        page = weblib.WebPage(name='', url=file_url)
        return page, ''
    else:
        title, comments, category = props
        name = title or p.name
        description = comments or ''
        tags = category or ''
        page = weblib.WebPage(name=name, description=description, url=file_url)
        return page, tags


def updateWebPage(page):
    """
    Update the corresponding file's NTFS summary property.
    @returns - pathname if data is updated, None otherwise
    """
    scheme, netloc, url_path, _, _, _ = urlparse.urlparse(page.url)
    assert scheme == 'file'
    p = path(util.nt_url2pathname(url_path))

    category = ', '.join(map(unicode,page.tags))
    # _writeProp() only work for read file
    # check this in advance to get friendlier error than the com_error
    if p.isfile():
        try:
            _writeProp(p, page.name, page.description, category)
            return p
        except (pywintypes.com_error, AttributeError), e:
            # file locked?
            log.exception('Unable to write NTFS property: %s' % p)
            return None
    else:
        # for directories or non-exist files, skip the writing.
        return None


def _readProp(pathname):
    """
    Read file properties using COM helper.
    @return - (title, comments, category)
    """
    pythoncom.CoInitialize()    # HACK need this per thread
    doc = win32com.client.Dispatch("DSOFile.OleDocumentProperties")
    doc.open(pathname)
    try:
        summary = doc.SummaryProperties
        result = summary.Title, summary.Comments, summary.Category
    finally:
        doc.close()
    return result


def _writeProp(pathname, title, comments, category):
    """
    Write file properties using COM helper.
    """
    pythoncom.CoInitialize()    # HACK need this per thread
    doc = win32com.client.Dispatch("DSOFile.OleDocumentProperties")
    doc.open(pathname)
    try:
        summary = doc.SummaryProperties
        summary.title = title
        summary.comments = comments
        summary.category = category
        doc.save()
    finally:
        doc.close()


def main(argv):
    if len(argv) < 2:
        print __doc__
        sys.exit(-1)
    pathname = argv[1]

    if len(argv) >= 5:
        title    = argv[2]
        comments = argv[3]
        category = argv[4]
    else:
        title, comments, category = '','',''

    # heuristics
    isURL = '://' in pathname

    if not isURL:
        # test lower level _readProp() and _writeProp()
        print 'Path:', pathname
        print 'props:', _readProp(pathname)

        if title or comments or category:
            _writeProp(pathname, title, comments, category)
            print
            print 'Updated props:', _readProp(pathname)
    else:
        # test high level makeWebPage() and updateWebPage()
        page, tags = makeWebPage(pathname)
        print '\nWebpage Info'
        print 'name       :', page
        print 'description:', page.description
        print 'url        :', page.url
        print 'tags       :', tags
        print
        if title or comments or category:
            page.name = title
            page.description = comments
            page.tags = []  # TODO: build tags from category
            updateWebPage(page)
            page, tags = makeWebPage(pathname)
            print '\nUpdate Webpage Info'
            print 'name       :', page
            print 'description:', page.description
            print 'url        :', page.url
            print 'tags       :', tags
            print


if __name__ =='__main__':
    main(sys.argv)
