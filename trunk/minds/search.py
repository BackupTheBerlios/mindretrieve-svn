"""
"""
import logging
import StringIO
import sys

from PyLucene import QueryParser, StandardAnalyzer
from PyLucene import Highlighter, QueryScorer, SimpleFragmenter, SimpleHTMLFormatter

from config import cfg
from minds import docarchive
from minds import distillparse
from minds import lucene_logic

log = logging.getLogger('search')


class MatchItem:
    def __init__(self, hits, key):
        self.index = 0
        self.doc = ''
        self.score = 0
        self.docid = ''
        self.zfile = None
        self.fp = None
        self.load(hits, key)

    def load(self, hits, key):
        self.index      = key
        self.doc        = hits.doc(key)
        self.score      = hits.score(key)
        self.docid      = self.doc.get('docid'      )
        self.date       = self.doc.get('date'       )
        self.uri        = self.doc.get('uri'        )
        self.title      = self.doc.get('title'      )
        self.description= self.doc.get('description')

    def highlight(self, analyzer, highlighter):
        maxNumFragmentsRequired = 2
        fp = docarchive.get_document(self.docid)
        meta, content = distillparse.parseDistillML(fp)
        tokenStream = analyzer.tokenStream('content', StringIO.StringIO(content))
        self.description = highlighter.getBestFragments(tokenStream, content, maxNumFragmentsRequired, "...")
        self.title = meta.get('title','')



def _padQueryTxt(query):
    return 'title:(%s) description:(%s) keywords:(%s) content:(%s)' % (query, query, query, query)


def parseQuery(phrase):
#    phrase = _padQueryTxt(phrase)
#    query = QueryParser.parse(phrase, "data", StandardAnalyzer())
    query = QueryParser.parse(phrase, "content", StandardAnalyzer())
    return query


def search(query, start, end):

    # search
    dbindex = cfg.getPath('archiveindex')
    searcher = lucene_logic.Searcher(pathname=dbindex)
    query = query.rewrite(searcher.reader.reader)
    hits = searcher.search(query)

    # prepare for highlighter
    formatter = SimpleHTMLFormatter("<span class='highlight'>", "</span>")
    highlighter = Highlighter( formatter, QueryScorer(query))
    highlighter.setTextFragmenter(SimpleFragmenter(50))
    analyzer = StandardAnalyzer()

    # build a MatchItem list
    result = []
    for i in xrange(start,end):
        if i >= hits.length():
            break
        item = MatchItem(hits, i)
        item.highlight(analyzer, highlighter)
        result.append(item)
    searcher.close()
    return hits.length(), result



### Testing ############################################################

def run():

    lastQuery = ''
    lastStart = 0

    while True:

        querystring = ''
        start = 0

        print
        print "Enter n for next page; p for previous page or no input to quite"
        command = raw_input("Query: ")

        if command == '':
            return

        elif command == 'n':
            querystring = lastQuery
            start = lastStart + 10

        elif command == 'p':
            querystring = lastQuery
            start = lastStart - 10

        else:
            querystring = command
            start = 0

        if not querystring or start < 0:
            continue

        print
        print "Searching for:", querystring

        query = parseQuery(querystring)
        length, result = search(query, start, start+10)

        lastQuery = querystring
        lastStart = start

        for item in result:
            print '\n%-2d' % (item.index+1),

            title = item.title and item.title or 'Untitled'
            print title.encode('latin-1','replace')[:100]

            if item.description:
                description = ' '.join(item.description.split())[:200]
                print '  ', description.encode('latin-1','replace')

            print '   %s' % item.date.replace('T', ' '),

            if item.uri:
                print item.uri.encode('latin-1','replace')[:100]
            else:
                print 'Address unknown'

        print
        print "%s/%s documents found." % (start, length)


def main(argv):
    from minds import proxy
    proxy.init(proxy.CONFIG_FILENAME)
    global cfg  #####
    cfg = proxy.cfg
    #print sys.getdefaultencoding()
    run()


if __name__ == '__main__':
    main(sys.argv)