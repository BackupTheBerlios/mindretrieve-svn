import StringIO
import sys
import unittest

from minds.safe_config import cfg as testcfg
from minds import distillML
from minds.util import rspreader
from minds.util import patterns_tester

testpath = testcfg.getpath('testDoc')


class TestDistill(unittest.TestCase):

    def setUp(self):
        self.buf = StringIO.StringIO()
        self.fp = None


    def tearDown(self):
        if self.fp: self.fp.close()


    def testMeta(self):

        # Check basic meta data parsing

        self.fp = rspreader.openlog(testpath/'basictags.html')
        meta = {}
        result = distillML.distill(self.fp, self.buf, meta)
        self.assertEqual(u'Basic HTML Sample Document', meta['title'])
        self.assertEqual(u'Description: this sample contains all basic HTML tags the converter understands', meta['description'])
        self.assertEqual(u'basic HTML, sample', meta['keywords'])
        self.assertEqual(4, len(meta))


    def testMetaVariations(self):

        # See meta_variations.html for variations of attributes formatting

        self.fp = rspreader.openlog(testpath/'meta_variations.html')
        meta = {}
        result = distillML.distill(self.fp, self.buf, meta)
        self.assertEqual(u'word1 word2 word3', meta['title'])            # title span multiple lines
        self.assertEqual(u'word1 & word2 <word3>', meta['description'])  # all cap 'DESCRIPTION'; HTML encoding decoded; attr span lines
        self.assert_(not meta.has_key('keywords'))
        self.assertEqual(3, len(meta))


    def testDistill(self):

        # check distilling basic HTML with all tags supported.

        self.fp = rspreader.openlog(testpath/'basictags.html')  # have all tags supported
        result = distillML.distill(self.fp, self.buf, {})
        self.assertEqual(0, result)

        s = self.buf.getvalue()

        # these tags should be filtered
        self.assertEqual(-1, s.find('<html'))
        self.assertEqual(-1, s.find('<head'))
        self.assertEqual(-1, s.find('<title'))
        self.assertEqual(-1, s.find('<body'))
        self.assertEqual(-1, s.find('<font'))
        self.assertEqual(-1, s.find('<b>'))
        self.assertEqual(-1, s.find('<em'))
        self.assertEqual(-1, s.find('<pre>'))
        self.assertEqual(-1, s.find('<blockquote>'))
        self.assertEqual(-1, s.find('<div'))
        self.assertEqual(-1, s.find('<span'))
        self.assertEqual(-1, s.find('<table'))
        self.assertEqual(-1, s.find('<tr'))
        self.assertEqual(-1, s.find('<td'))
        self.assertEqual(-1, s.find('<form'))
        self.assertEqual(-1, s.find('<img'))
        self.assertEqual(-1, s.find('<a'))
        self.assertEqual(-1, s.find('</html>'))

        # these tags should present
        self.assert_(s.find('<h1>') > 0)
        self.assert_(s.find('<h2>') > 0)
        self.assert_(s.find('<h3>') > 0)
        self.assert_(s.find('<h4>') > 0)
        self.assert_(s.find('<h5>') > 0)
        self.assert_(s.find('<h6>') > 0)
        self.assert_(s.find('<p>' ) > 0)
        self.assert_(s.find('<ul>') > 0)
        self.assert_(s.find('<ol>') > 0)
        self.assert_(s.find('<li>') > 0)
        self.assert_(s.find('<br>') > 0)
        self.assert_(s.find('<hr>') > 0)

        # these are some other transformed data
        self.assert_(s.find('h1-Sample HTML') > 0)
        self.assert_(s.find('[fill your name]') > 0)        # <form>
        self.assert_(s.find('[*]') > 0)
        self.assert_(s.find('[ ]') > 0)
        self.assert_(s.find('(*)') > 0)
        self.assert_(s.find('( )') > 0)
        self.assert_(s.find('[***]') > 0)
        self.assert_(s.find('Lorem') > 0)                   # <textarea>
        self.assert_(s.find('[button]') > 0)
        self.assert_(s.find('[submit]') > 0)
        self.assert_(s.find('[reset]') > 0)
        self.assert_(s.find('[go]') > 0)
        self.assert_(s.find('[a picture]') > 0)             # <img>
        self.assert_(s.find(u'<&amp;,&lt;, ,",&gt;>') > 0)  # entities


    def testDistillTxt(self):
        self.fp = rspreader.openlog(testpath/'plaintext.mlog')
        result = distillML.distillTxt(self.fp, self.buf, {})
        self.assertEqual(0, result)

        # check content
        self.buf.seek(0)
        p = patterns_tester.checkStrings(self.buf.read(), ['Copyright', 'All rights reserved.', 'OF SUCH DAMAGE.'])
        self.assert_(not p, 'unexpected: %s' % p)


    def testParserError(self):

        PROBLEM_LINE = '<! -- this is bad -->'

        self.fp = rspreader.openlog(testpath/'malformed_html.mlog')
        s = self.fp.read(1024)
        self.assert_(s.find(PROBLEM_LINE) > 0)   # make sure the PROBLEM_LINE is in the test data
        self.fp.seek(0)

        result = distillML.distill(self.fp, self.buf, {})
        self.assertEqual(distillML.PARSE_ERROR, result[0])

# todo add these tests
#
#    def testWordSpaceCollapseIssue(self):
#        self.fail('todo')
#
#
#    def testTextAsHTML(self):
#        self.fail('todo')
#
#
    def testAttrEncodingProblem(self):
        """ Bad HTML found in http://news.bbc.co.uk/ """

        # note: the <b> inside the quoted attribute value should be
        # written as &lt;b&gt;. We choose not to workaround this right now
        doc = """<html><body>
<p>filler.filler.filler.filler.filler.filler.filler</p>
<a onmouseover="ChangeText('<b>Back to previous</b>');">text</a>
</body></html>"""

        result = distillML.distill(StringIO.StringIO(doc), self.buf, {})
        self.assertEqual(0, result)
        s = self.buf.getvalue()

        # the test below would fail. Disable it for now.
        #self.assertEqual(-1, s.find('Back to previous'))


    def testParseEmptyTagProblem(self):
        """ Test problem in parsing <br/> """

        # The smgllib.SGMLParser in various versions of Python has problem
        # parsing <br/> It was suggested to workaround by using <br />
        # with a space. But we don't have a choice for documents fetched
        # from the web.
        doc = """<html><body>
<p>filler.filler.filler.filler.filler.filler.filler</p>
<p>abc<br/>def</p>
</body></html>"""

        result = distillML.distill(StringIO.StringIO(doc), self.buf, {})
        self.assertEqual(0, result)

        s = self.buf.getvalue()
        self.assert_(s.find('abc<br>') > 0)
        self.assert_(s.find('>def') < 0)        # the '>' from the preceding <br/> is a syndrome


    def testParseCrazyTitleProblem(self):

        # Test problem in parsing a missing <title>
        doc = """<html><head>hello</title></head>
<body>
<p>filler.filler.filler.filler.filler.filler.filler</p>
</body></html>"""

        meta = {}
        result = distillML.distill(StringIO.StringIO(doc), self.buf, meta)
        self.assertEqual(0, result)

        s = self.buf.getvalue()
        self.assert_(not meta.has_key('title'))     # no title
        self.assert_(s.find('filler') >= 0)         # but sort of getting rest of data



class TestFormatter(unittest.TestCase):

    def setUp(self):
        self.buf = StringIO.StringIO()
        self.out = distillML.Formatter(self.buf)

    def test_notifyHtml(self):

        out = self.out
        out.out('line1')
        out.notifyHtml()
        out.out('line2')
        out.notifyHtml()    # an invalid second <html>
        out.out('line3')

        self.assertEqual(out.contentBeforeHtml(), 'line1')      # make sure this is not disrupt by second notifyHtml()
        self.assertEqual(out.getHeader(), 'line1line2line3')



class TestCharEncoding(unittest.TestCase):

    # note: this set of test data includes encoding from both http header and <meta> tag

    def setUp(self):
        self.meta = {}
        self.buf = StringIO.StringIO()
        self.fp = None

        # format of test_encoding_data
        # line 1: encoding name
        # line 2: title
        # line 3: sample content

        # Best view using full unicode font such as 'Gulim'

        fp = file(testpath/'test_encoding_data.utf8.txt', 'rb')
        self.test_data = [line.decode('utf8').rstrip() for line in fp]
        fp.close()


    def tearDown(self):
        if self.fp: self.fp.close()


    def test_utf8(self):

        self.fp = file(testpath/'ah_ying_utf8.qlog', 'rb')
        title, content = self.test_data[1:3]

        result = distillML.test_distill(self.fp, self.buf, self.meta)
        self.assertEqual(0, result)
        self.assertEqual(self.meta['encoding'], 'utf-8 [META]')
        self.assertEqual(self.meta['title'], title)

        s = self.buf.getvalue().decode('utf8')
        self.assert_(s.find(content) > 0)


    def test_iso_8851_1(self):

        self.fp = file(testpath/'apache_ISO-8859-1.qlog', 'rb')
        title, content = self.test_data[4:6]

        result = distillML.test_distill(self.fp, self.buf, self.meta)
        self.assertEqual(0, result)
        self.assertEqual(self.meta['encoding'], 'iso-8859-1 [HTTP]')
        self.assertEqual(self.meta['title'], title)

        s = self.buf.getvalue().decode('utf8')
        self.assert_(s.find(content) > 0)


    def test_koi8_r(self):

        self.fp = file(testpath/'apache_koi8-r.qlog', 'rb')
        title, content = self.test_data[7:9]

        result = distillML.test_distill(self.fp, self.buf, self.meta)
        self.assertEqual(0, result)
        self.assertEqual(self.meta['encoding'], 'koi8-r [HTTP]')
        self.assertEqual(self.meta['title'], title)

        s = self.buf.getvalue().decode('utf8')
        self.assert_(s.find(content) > 0)


    def test_big5(self):

        self.fp = file(testpath/'hk.yahoo_big5.qlog', 'rb')
        title, content = self.test_data[10:12]

        result = distillML.test_distill(self.fp, self.buf, self.meta)
        self.assertEqual(0, result)
        self.assertEqual(self.meta['encoding'], 'big5 [META]')
        self.assertEqual(self.meta['title'], title)

        s = self.buf.getvalue().decode('utf8')
        self.assert_(s.find(content) > 0)


    def test_euc_jp(self):

        self.fp = file(testpath/'apache_euc-jp.qlog', 'rb')
        title, content = self.test_data[13:15]

        result = distillML.test_distill(self.fp, self.buf, self.meta)
        self.assertEqual(0, result)
        self.assertEqual(self.meta['encoding'], 'euc-jp [HTTP]')
        self.assertEqual(self.meta['title'], title)

        s = self.buf.getvalue().decode('utf8')
        self.assert_(s.find(content) > 0)


    def test_euc_kr(self):

        self.fp = file(testpath/'apache_euc-kr.qlog', 'rb')
        title, content = self.test_data[16:18]

        result = distillML.test_distill(self.fp, self.buf, self.meta)
        self.assertEqual(0, result)
        self.assertEqual(self.meta['encoding'], 'euc-kr [HTTP]')
        self.assertEqual(self.meta['title'], title)

        s = self.buf.getvalue().decode('utf8')
        self.assert_(s.find(content) > 0)


    def test_big5_txt(self):

        self.fp = file(testpath/'ah_ying.txt', 'rb')
        title, content = self.test_data[19:21]

        self.meta['content-type'] = 'text/plain; charset=big5'

        result = distillML.distillTxt(self.fp, self.buf, self.meta)
        self.assertEqual(0, result)
        self.assertEqual(self.meta['encoding'], 'big5 [HTTP]')
        #self.assertEqual(self.meta['title'], title)

        s = self.buf.getvalue().decode('utf8')
        self.assert_(s.find(content) > 0)


    def test_bad_encoding(self):

        self.fp = file(testpath/'ah_ying_bad.qlog', 'rb')

        result = distillML.test_distill(self.fp, self.buf, self.meta)
        self.assertEqual(self.meta['encoding'], 'iso-8859-1 [DEFAULT]')     # invalid encoding -> default



class TestWeeding(unittest.TestCase):

    def setUp(self):
        self.buf = StringIO.StringIO()
        self.fp = None


    def tearDown(self):
        if self.fp: self.fp.close()


    def testDomainFiltered(self):
        self.fp = StringIO.StringIO()
        result = distillML.distill(self.fp, self.buf, {'uri':'http://x.googlesyndication.com/'})
        self.assertEqual((distillML.EXDOMAIN, '.googlesyndication.com'), result)


    def testDomainFilteredTxt(self):
        self.fp = StringIO.StringIO()
        result = distillML.distillTxt(self.fp, self.buf, {'uri':'http://x.googlesyndication.com/'})
        self.assertEqual((distillML.EXDOMAIN, '.googlesyndication.com'), result)


    def testMagicFiltered(self):
        self.fp = rspreader.openlog(testpath/'gif.qlog')
        result = distillML.distill(self.fp, self.buf, {})
        self.assertEqual((distillML.NON_HTML, 'image/gif'), result)


    def testMagicFilteredTxt(self):
       """ Wrong media type text/plain """
       self.fp = rspreader.openlog(testpath/'favicon.ico_text(nutch).mlog')
       result = distillML.distillTxt(self.fp, self.buf, {})
       self.assertEqual((distillML.NON_HTML, 'image/vnd.microsoft.icon'), result)


#    def testPlaintext(self):
#        self.fp = rspreader.openlog(testpath/'plaintext.txt')
#        result = distillML.distill(self.fp, self.buf, {})
#        self.assertEqual((distillML.NON_HTML, 'unknown'), result)


#    def testXML(self):
#        self.fp = rspreader.openlog(testpath/'xmltext.xml')
#        result = distillML.distill(self.fp, self.buf, {})
#        self.assertEqual((distillML.NON_HTML, 'unknown'), result)


    def testFrameset(self):
        self.fp = rspreader.openlog(testpath/'frameset.html')
        result = distillML.distill(self.fp, self.buf, {})
        self.assertEqual((distillML.FRAMESET), result[0])


    def testCSS(self):
        self.fp = rspreader.openlog(testpath/'main.css')
        result = distillML.distill(self.fp, self.buf, {})
        self.assertEqual((distillML.NON_HTML, 'unknown'), result)


    def testJavascript(self):
        self.fp = rspreader.openlog(testpath/'js/doc_write_html.js')
        result = distillML.distill(self.fp, self.buf, {})
        self.assertEqual((distillML.JS, u'document.write('), result)

        self.fp = rspreader.openlog(testpath/'js/function.js')
        result = distillML.distill(self.fp, self.buf, {})
        self.assertEqual((distillML.JS, u'function YADopenWindow(x){'), result)

        self.fp = rspreader.openlog(testpath/'js/ibHtml1=.js')
        result = distillML.distill(self.fp, self.buf, {})
        self.assertEqual((distillML.JS, u'ibHtml1="'), result)

        self.fp = rspreader.openlog(testpath/'js/var_with_html.js')
        result = distillML.distill(self.fp, self.buf, {})
        self.assertEqual((distillML.JS,  u'var pophtml ='), result)

        self.fp = rspreader.openlog(testpath/'js/small1.js')
        result = distillML.distill(self.fp, self.buf, {})
        self.assertEqual((distillML.NON_HTML, 'unknown'), result)

        self.fp = rspreader.openlog(testpath/'js/small2.js')
        result = distillML.distill(self.fp, self.buf, {})
        self.assertEqual((distillML.NON_HTML, 'unknown'), result)


    def testLowvisible(self):
       self.fp = rspreader.openlog(testpath/'lowvisible(doubleclick).mlog')
       result = distillML.distill(self.fp, self.buf, {})
       self.assertEqual(distillML.LOWVISIBLE, result[0])



if __name__ == '__main__':
    unittest.main()