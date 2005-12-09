import StringIO
import sys
import unittest
import urllib

from minds.cgibin.util import response

TEST_HTML_TEMPLATE = u"""<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<script>
alert("%s");
</script>"""

class TestResponse(unittest.TestCase):

    def test_javascriptEscape(self):
        text = u"""You should see
1. new line separate by \\n.\r
2. new line separate by \\r\\n.
3. quote ' and double quote ".
4. The slash \\ character.
5. The euro sign \N{euro sign}.
"""
        escaped_test = response.javascriptEscape(text)

        print '\nPlease cut and paste the statement below and test in your browser'
        print '-'*72
        print (TEST_HTML_TEMPLATE % escaped_test).encode('utf8')
        print '-'*72

        self.assert_('.\\r\\n' in escaped_test)
        self.assert_('\\"' in escaped_test)
        self.assert_("\\'" in escaped_test)
        self.assert_('\\\\' in escaped_test)


if __name__ == '__main__':
    unittest.main()