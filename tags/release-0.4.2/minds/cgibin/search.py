import cgi
import codecs
import os, sys

from minds.config import cfg
from minds import search
from minds.util import pagemeter
import searchTmpl


PAGE_SIZE = 10


class QueryForm:

  def __init__(self, fields):
    self.query = ''
    self.start = 0
    self._parse_form(fields)


  def _parse_form(self, fields):

    _q = fields.getfirst('query')
    if _q:
        self.query = _q.decode('utf8','ignore').strip()

    self.start = fields.getfirst('start')
    try:
        self.start = int(self.start)
    except:
        self.start = 0


  def makeQueryString(self, start=0):
    uri = 'search?query=%s&start=%s' % (
        cgi.escape(self.query),
        start,
        )
    return uri



def main(rfile, wfile, env):

    form = cgi.FieldStorage(fp=rfile, environ=env)
    qform = QueryForm(form)

    error_msg = ''
    num_match = 0
    matchList = []
    if qform.query:
        try:
            query = search.parseQuery(qform.query)
        except Exception, e:
            error_msg = e.args[0].split('\n')[0]
        else:
            num_match, matchList = search.search(query, qform.start, qform.start+PAGE_SIZE)

    page = pagemeter.PageMeter(qform.start, num_match, PAGE_SIZE)
    title = 'MindRetrieve query: %s' % qform.query

    wfile.write(
"""Content-type: text/html; charset=UTF-8\r
Cache-control: no-cache\r
\r
""")

    sw = codecs.getwriter('utf-8')
    wfile = sw(wfile,'replace')

    from minds import app_httpserver
    app_httpserver.forwardTmpl(wfile, env, 'search.html',
        searchTmpl, qform, page, title, qform.query, error_msg, matchList)

###    wfile.write(query_string.encode('string_escape')+'\n')
###    wfile.write(env['QUERY_STRING'].encode('unicode_escape')+'\n')

if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)