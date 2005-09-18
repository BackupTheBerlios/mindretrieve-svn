"""
"""
import logging
import StringIO
import sys

from PyLucene import QueryParser, StandardAnalyzer
from PyLucene import Highlighter, QueryScorer, SimpleFragmenter, SimpleHTMLFormatter

from minds.config import cfg
from minds import docarchive
from minds import distillparse
from minds import lucene_logic

log = logging.getLogger('search')


class MatchItem:
    def __init__(self, hits, key):

        # lucene data
        self.index      = key   # hits index
        self.id         = 0     # id
        self.doc        = None  # Document
        self.score      = 0     # adjusted score
        self.score0     = 0     # original Lucene score

        # doument meta-data
        self.docid      = ''
        self.date       = ''
        self.uri        = ''
        self.title      = ''
        self.description= ''

        self.load(hits, key)


    def load(self, hits, key):
        self.id         = hits[key][1]
        self.doc        = hits[key][2]
        self.score      = hits[key][0]
        self.score0     = hits[key][3]

        self.docid      = self.doc.get('docid'      )
        self.date       = self.doc.get('date'       )
        self.uri        = self.doc.get('uri'        )

        # title & description are filled at hightlight()


    def highlight(self, analyzer, highlighter):
        maxNumFragmentsRequired = 2
        try:
            fp = docarchive.get_document(self.docid)
        except Exception, e:
            # maybe the index is outdate to refer to some non-exist file
            log.exception('Unable to get "%s"' % self.docid)
        else:
            meta, content = distillparse.parseDistillML(fp)
            tokenStream = analyzer.tokenStream('content', StringIO.StringIO(content))
            self.description = highlighter.getBestFragments(tokenStream, content, maxNumFragmentsRequired, "...")
            self.title = meta.get('title','')


    def __str__(self):
        return 'matchItem<%s,%s,%s>' % (self.id, self.docid, self.uri)



def parseQuery(phrase):
    query = QueryParser.parse(phrase, "content", StandardAnalyzer())
    return query


MAXRESULT = 1000

def sortHits(hits, maxDoc):
    """ Return list of (adj score, id, doc, original score) """
    hitList = []
    for i in xrange(min(1000,hits.length())):
        id = hits.id(i)
        score = hits.score(i)
        date_adjusted = score / (maxDoc - id)
        hitList.append((date_adjusted, id, hits.doc(i), score))

    if not hitList:
        return []

    hitList.sort(reverse=True)

    # normalize score
    high_score = hitList[0][0]
    hitList = [(s/high_score, id, doc, score0) for s,id,doc,score0 in hitList]

    return hitList



def search(query, start, end):

    # search
    indexpath = cfg.getpath('archiveindex')
    searcher = lucene_logic.Searcher(pathname=indexpath)
    query = query.rewrite(searcher.reader.reader)
    hits = searcher.search(query)

    hitList = sortHits(hits, searcher.reader.maxDoc()+2000)

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
        item = MatchItem(hitList, i)
        try:
            item.highlight(analyzer, highlighter)
        except Exception, e:
            log.exception('Error highlighting %s' % item);
        #item.explaination = str(searcher.explain(query, item.id))
        result.append(item)

    searcher.close()
    return hits.length(), result



### Testing ############################################################

def encode(s):
    return s.encode('cp437','replace')      # windows console


def run_search(querystring, start):

    query = parseQuery(querystring)

    print '\n-----------------------------------'
    print "Searching for:", querystring
    print "Query: " + str(query)
    print '-----------------------------------'

    length, result = search(query, start, start+10)

    for item in result:
        print '\n%-2d' % (item.index+1),

        title = item.title and item.title or 'Untitled'
        print encode(title[:100])

        if item.description:
            description = ' '.join(item.description.split())
            print '  ', encode(description)

        print '   %s %0.5f %0.5f %s' % (item.id, item.score, item.score0, item.date.replace('T', ' ')),

#        print '\n\n%s' % item.explaination ###

        if item.uri:
            print encode(item.uri[:100])
        else:
            print 'Address unknown'

    print "\nFrom %s of %s documents found." % (start, length)


def main(argv):

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

        lastQuery = querystring
        lastStart = start

        run_search(querystring, start)


if __name__ == '__main__':
    main(sys.argv)