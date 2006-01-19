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
#import win32com.client
from win32com import storagecon

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
        # extract name from last part of path
        head, tail = os.path.split(p)
        if head and not tail:   # i.e. end in trailing \
            head, tail = os.path.split(head)
        page = weblib.WebPage(name=tail, url=file_url)
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
    Read file properties using IPropertySetStorage.
    @return - (title, comments, category)
    """
    pss = None
    pssum = None
    psdocs = None
    try:
      try:
        ##  file, mode, format, attrs (always 0), IID (IStorage or IPropertySetStorage, storage options(only used with STGFMT_DOCFILE)
        pss=pythoncom.StgOpenStorageEx(pathname,
            storagecon.STGM_READWRITE | storagecon.STGM_SHARE_EXCLUSIVE,
            storagecon.STGFMT_FILE,
            0 ,
            pythoncom.IID_IPropertySetStorage)

        pssum = pss.Open(pythoncom.FMTID_SummaryInformation, storagecon.STGM_READ | storagecon.STGM_SHARE_EXCLUSIVE)
        title, comments = pssum.ReadMultiple((storagecon.PIDSI_TITLE, storagecon.PIDSI_COMMENTS))

        psdocs = pss.Open(pythoncom.FMTID_DocSummaryInformation, storagecon.STGM_READ | storagecon.STGM_SHARE_EXCLUSIVE)
        category = psdocs.ReadMultiple((storagecon.PIDDSI_CATEGORY,))[0]

        return title, comments, category

      except pywintypes.com_error, e:
        #import traceback
        #traceback.print_exc()
        # STG_E_FILENOTFOUND or STG_E_ACCESSDENIED?
        return ('','','')

    finally:
        ## doesn't seem to be a close or release method, and you can't even reopen it from the same process until previous object is gone
        psdocs = None
        pssum = None
        pss = None


def _writeProp(pathname, title, comments, category):
    """
    Write file properties using IPropertySetStorage.
    """
    # code base on pywin32 - win32com\test\testStorage.py
    pss = None
    pssum = None
    psdocs = None
    try:
        ##  file, mode, format, attrs (always 0), IID (IStorage or IPropertySetStorage, storage options(only used with STGFMT_DOCFILE)
        pss=pythoncom.StgOpenStorageEx(pathname,
            storagecon.STGM_READWRITE | storagecon.STGM_SHARE_EXCLUSIVE,
            storagecon.STGFMT_FILE,
            0 ,
            pythoncom.IID_IPropertySetStorage)

        pssum = _openPropertySet(pss, pythoncom.FMTID_SummaryInformation)
        pssum.WriteMultiple((storagecon.PIDSI_TITLE,storagecon.PIDSI_COMMENTS),(title, comments))

        psdocs = _openPropertySet(pss, pythoncom.FMTID_DocSummaryInformation)
        psdocs.WriteMultiple((storagecon.PIDDSI_CATEGORY,),(category,))

    finally:
        ## doesn't seem to be a close or release method, and you can't even reopen it from the same process until previous object is gone
        psdocs = None
        pssum = None
        pss = None


def _openPropertySet(pss, fmtid):
    """ Helper to open fmtid. Create if not already exist """
    try:
        # try Open() first
        ps=pss.Open(fmtid, storagecon.STGM_READWRITE|storagecon.STGM_SHARE_EXCLUSIVE)
    except pywintypes.com_error, e:
        if e.args[1] != 'STG_E_FILENOTFOUND': raise
        # if STG_E_FILENOTFOUND try Create()
        ps=pss.Create(fmtid,
                      pythoncom.IID_IPropertySetStorage,
                      storagecon.PROPSETFLAG_DEFAULT,
                      storagecon.STGM_READWRITE|storagecon.STGM_CREATE|storagecon.STGM_SHARE_EXCLUSIVE)
    return ps


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
