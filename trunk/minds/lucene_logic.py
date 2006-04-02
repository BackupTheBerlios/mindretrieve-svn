"""
Wrap lucene's IndexReader, IndexWriter and IndexSearcher.
Provide a few methods for use with MindRetrieve.
"""

import logging
import os, os.path, sys
import traceback

import PyLucene
from minds.config import cfg

__all__ = [
    'initDirectory',
    'openDirectory',
    'Reader',
    'Writer',
    'Searcher',
]

log = logging.getLogger('lucene')

def initDirectory(directory):
    """ initialize a new directory """
    writer = PyLucene.IndexWriter(directory, PyLucene.StandardAnalyzer(), True)

    version = cfg.get('_system.version', '?')
    doc = PyLucene.Document()
    doc.add(PyLucene.Field('version', version, True, True, False))

    # the date field is not used in this document. However it is added
    # to avoid an error when using Sort('date') when there is no date
    # Term in the index.
    doc.add(PyLucene.Field('date', '', True,  True, False))

    writer.addDocument(doc)

    writer.close()


def openDirectory(pathname=None):
    """ pathname - index directory. Create new index if directory
        does not exist. '' or None for RAMDirectory (for testing).
    """
    if not pathname:
        directory = PyLucene.RAMDirectory()
        initDirectory(directory)

    elif not os.path.exists(pathname):
        directory = PyLucene.FSDirectory.getDirectory(pathname, True)
        initDirectory(directory)

    else:
        directory = PyLucene.FSDirectory.getDirectory(pathname, False)

    return directory



class Reader(object):
    """ Create a lucene IndexReader """

    def __init__(self, pathname=None, directory=None):
        """ pathname - index directory. Create new index if directory
            does not exist. '' or None for RAMDirectory (for testing).
        """
        if directory and pathname:
            raise ValueError, 'Only one of pathname or directory should be set'
        elif directory:
            self.directory = directory
        else:
            self.directory = openDirectory(pathname)

        try:
            PyLucene.IndexReader.unlock(self.directory) ###HACK!!! TODO!!
            self.reader = PyLucene.IndexReader.open(self.directory)
        except:
            log.error('Error creating IndexWriter pathname=%s directory=%s', pathname, directory)
            raise


    def __getattr__(self, attr):
        """ delegate to the underlying object """
        return getattr(self.reader, attr)


    def getVersion(self):
        tenum = self.reader.terms( PyLucene.Term('version', '') )
        if tenum.term(): return tenum.term().text()
        return ''


    def hasDocument(self, docid):
        term = PyLucene.Term('docid', docid)
        termEnum = self.reader.terms(term)
        return termEnum.term() and (termEnum.term().compareTo(term) == 0)


    def deleteDocuments(self, docid):
        term = PyLucene.Term('docid', docid)
        # corresponds to IndexReader.delete(Term term) in Java
        return self.reader.deleteDocuments(term)


    def __str__(self):
        if not self.reader: return 'reader=None'
        return 'IndexReader[numDocs %s directory %s]' % (self.reader.numDocs(), self.directory)



class Writer(object):
    """ Create a IndexWriter for adding documents """

    def __init__(self, pathname=None):
        self.directory = openDirectory(pathname)
        try:
            self.writer = PyLucene.IndexWriter(self.directory, PyLucene.StandardAnalyzer(), False)
        except:
            log.error('Error creating IndexWriter pathname=' + pathname)
            raise
        self.writer.maxFieldLength = 1048576 ########<<< todo: ????


    def __getattr__(self, attr):
        """ delegate to the underlying object """
        return getattr(self.writer, attr)


    def addDocument(self, docid, meta, content):
        """ Add a document with uri, date, title, description, keywords, etag and content fields.
            meta and content should be in unicode
        """

        uri           = meta.get('uri'          ,'')
        date          = meta.get('date'         ,'')
        etag          = meta.get('etag'         ,'')
        last_modified = meta.get('last-modified','')

        if not etag: etag = last_modified

        doc = PyLucene.Document()
        doc.add(PyLucene.Field("docid"  , docid  , True,  True, False))
        doc.add(PyLucene.Field("content", content, False, True, True ))
        if uri : doc.add(PyLucene.Field('uri'  , uri , True,  True,  False))
        if date: doc.add(PyLucene.Field('date' , date, True,  True,  False))
        if etag: doc.add(PyLucene.Field('etag' , etag, True,  False, False))

        self.writer.addDocument(doc)


    def __str__(self):
        if not self.writer: return 'writer=None'
        return 'IndexWriter[docCount %s directory %s]' % (self.writer.docCount(), self.directory)



class Searcher(object):
    """ Create a IndexSearcher """

    def __init__(self, **args):
        """ pathname - index directory. Create new index if directory
            does not exist. '' or None for RAMDirectory (for testing).
        """
        self.reader = Reader(**args)
        self.searcher = PyLucene.IndexSearcher(self.reader.reader)


    def __getattr__(self, attr):
        """ delegate to the underlying object """
        return getattr(self.searcher, attr)


    def searchLast(self, uri):
        """ Search on uri and etag defined in meta """

        # the Sort below won't work if the are no document
        if self.reader.reader.maxDoc() <= 0:
            return False
        tq = PyLucene.TermQuery(PyLucene.Term('uri', uri))
        return self.searcher.search(tq, PyLucene.Sort('date', True))


    def close(self):
        try:
            if self.searcher: self.searcher.close()
        finally:
            try:
                if self.reader: self.reader.close()
            except: # avoid throwing exception in finally clause
                log.exception('Problem in IndexReader.close()')



def showHits(hits, *args):
    """ A helper function to show the result of a Hits """
    print 'length:', hits.length()
    for i in xrange( min(20,hits.length()) ):
        print '\ndid:', hits.id(i)
        doc = hits.doc(i)
        for f in args:
            print f + ': ' + str(doc.get(f))



########################################################################

# Code to show Lucene holds GIL and blocks all threads.

########################################################################

import time,threading

def threadMain(threadid):
    for i in range(40):
        print 'id %s - %s' %(threadid,i)
        time.sleep(0.3)

def luceneMain():
    time.sleep(0.8)
    writer = Writer('testdb/index')
    print 'docCount=',writer.writer.docCount()
    writer.addDocument('12345', {}, 'this is a document')
    writer.writer.optimize()
    writer.writer.close()
    print 'writer done'

def thread_test():
    threads = []
    for i in range(5):
        threads.append(threading.Thread(target=threadMain, args=(i,)))
    for t in threads:
        t.start()
    luceneMain()
    for t in threads:
        t.join()

########################################################################

def shell(argv):
    print __doc__

    # does this provide some kind of restriction to prevent misuse?
    if __name__ != '__main__':
        print >>sys.stderr, 'shell() can only be launched from command line.'
        sys.exit(-1)

    local = {}
    exec 'from minds.lucene_logic import *'in local
    while True:
        line = raw_input('lucene> ')
        if not line:
            break
        try:
            exec line in local

        except:
            traceback.print_exc()


if __name__ == '__main__':
    #luceneMain()
    #thread_test()
    shell(sys.argv)