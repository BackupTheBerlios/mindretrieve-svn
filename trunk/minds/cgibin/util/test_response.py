import StringIO
import sys
import unittest
import urllib

from minds.cgibin.util import response

TEST_HTML_TEMPLATE = u"""<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<script>
alert("%s");
</script>"""


class SampleRenderer(response.CGIRenderer):
    TEMPLATE_FILE = 'weblibForm.html'
    def render(self,node):
        pass


class SampleWeblibLayoutRenderer(response.WeblibLayoutRenderer):
    TEMPLATE_FILE = 'weblibContent.html'
    def render(self,node):
        pass


class TestResponse(unittest.TestCase):

    def test_redirect(self):
        url = u'http://www.\N{euro sign}.com/'
        buf = StringIO.StringIO()
        response.redirect(buf, url)
        # this URL is actually registered!
        self.assert_('http://www.%E2%82%AC.com/' in buf.getvalue())


    def test_jsEscapeString(self):
        text = u"""You should see
1. new line separate by \\n.\r
2. new line separate by \\r\\n.
3. quote ' and double quote ".
4. The slash \\ character.
5. The angle brackets < and >.
6. The euro sign \N{euro sign}.
"""
        escaped_test = response.jsEscapeString(text)

        print '\nPlease cut and paste the statement below and test in your browser'
        print '-'*72
        print (TEST_HTML_TEMPLATE % escaped_test).encode('utf8')
        print '-'*72

        self.assert_('.\\r\\n' in escaped_test)
        self.assert_('\\"' in escaped_test)
        self.assert_("\\'" in escaped_test)
        self.assert_('\\\\' in escaped_test)
        self.assert_('<'  not in escaped_test)
        self.assert_('>' not in escaped_test)


    def test_buildBookmarklet(self):
        # sanity run
        url = response.buildBookmarklet()
        self.assert_('http://localhost:' in url)


    def test_CGIRenderer(self):
        buf = StringIO.StringIO()
        SampleRenderer(buf).output()
        # Render is fairly completed to check. CGI test would better verify them.
        # Just do some sanity check on the output here
        self.assert_('</html>' in buf.getvalue())


    def test_WeblibLayoutRenderer(self):
        buf = StringIO.StringIO()
        SampleWeblibLayoutRenderer(buf).output()
        # Render is fairly completed to check. CGI test would better verify them.
        # Just do some sanity check on the output here
        self.assert_('</html>' in buf.getvalue())


    def test_split_style_block(self):
        def _test(text,expected):
            self.assertEqual(response._split_style_script_block(text), expected)

        _test('abc <style> def</style>ghi', ('<style> def</style>', '', 'abc ghi'))
        _test('abc def ghi', ('', '', 'abc def ghi'))                # ok if no <style>
        _test('abc <style>def ghi', ('', '', 'abc <style>def ghi'))  # must come in pair

        # with script
        _test('abc <script>var i=1;</script>ghi', ('', '<script>var i=1;</script>', 'abc ghi'))

        # with style and script
        _test('abc <style>!</style> <script>var i=1;</script>ghi', ('<style>!</style>', '<script>var i=1;</script>', 'abc  ghi'))


if __name__ == '__main__':
    unittest.main()