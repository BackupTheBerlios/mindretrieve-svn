import os.path
import StringIO
import unittest

from minds.util import html_pull_parser as hpp

DATA   = hpp.DATA
TAG    = hpp.TAG
ENDTAG = hpp.ENDTAG
COMMENT= hpp.COMMENT

DOC = u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3c.org/TR/html4/loose.dtd">
<html>
<head>
<title>a title</title>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">
<link rel="stylesheet" href="/main.css" type="text/css">
</head>
<body>
<!--this is a comment-->
text

<p>gt=&gt;
<p>aring=&aring;
<p>Aring=&Aring;

<p>229=&#229;
<p>e5=&#xe5;
<p>E5=&#XE5;
<p>1048=&#1048;

</body>
</html>
"""

class ChunkedStringIO(object):
    """ Helper to feed SGMLParser with incomplete string chunks """

    def __init__(self, chunks):
        self.chunks = chunks

    def read(self, bufsize=-1):
        if not self.chunks:
            return None
        return self.chunks.pop(0)



class BaseTest(unittest.TestCase):

    DEBUG = 0

    def _test_generator(self, doc, expect, **args):
        fp = StringIO.StringIO(doc)
        tokens = hpp.generate_tokens(fp, **args)
        self._test_generator1(tokens, expect)


    def _test_generator1(self, tokens, expect):
        k = 0
        for t in tokens:
            if self.DEBUG: print t
            if k < len(expect) and t == expect[k]:
                k += 1
        self.assertEqual(expect[k:k+1], [])



class TestParser(BaseTest):

    def test_parse(self):

        self._test_generator(
            DOC, [

            (TAG,    u'html', []),      # match some start tag
            (DATA,   u'a title'),       # match some text

            (DATA,   u'gt='),
            (DATA,   u'&gt;'),          # retain &gt;

            (DATA,   u'aring='),
            (DATA,   u'\xe5'),          # lowercase entity ref

            (DATA,   u'Aring='),
            (DATA,   u'\xc5'),          # upper case entity ref

            (DATA,   u'229='),
            (DATA,   u'\u00e5'),        # decimal case character ref

            (DATA,   u'e5='),
            (DATA,   u'\u00e5'),        # hex lower case character ref

            (DATA,   u'E5='),
            (DATA,   u'\u00e5'),        # hex upper case character ref

            (ENDTAG, u'html'),          # match some end tag

            ])

    def test_no_retain(self):
        self._test_generator(
            DOC,
            [
             (DATA,   u'gt='),
             (DATA,   u'>'),            # entity translated
             (TAG,    u'p', []),
             (DATA,   u'aring='),
            ],
            keep_entity_ref={}          # suppress the keep_entity_ref feature
            )

    def test_comment(self):
        self._test_generator(
            DOC, [
             (COMMENT,  u'this is a comment'),
             (DATA,     u'\ntext\n\n'),
            ],
            comment=True,               # turn on the comment feature
            )


class TestSGMLPatch(BaseTest):

    def test_declaration_good_case(self):
        self._test_generator(
            "<html>A<!-- good comment -->B</html>",
            [
            (TAG,    u'html', []),
            (DATA,   u'A'       ),
            (DATA,   u'B'       ),
            (ENDTAG, u'html'),
            ])


    def test_parse_emptytag(self):

        # verify workaround of sgmllib's problem in handling empty tag construct. e.g. <br/>, <hr />

        self._test_generator(
            "<html><br/><hr /><p>!</html>",
            [
            (TAG,    u'html', []),
            (TAG,    u'br',   []),      # get the start tag
            (TAG,    u'hr',   []),      # get the start tag
            (TAG,    u'p',    []),      # and next tag
            (DATA,   u'!',      ),      # and some text
            (ENDTAG, u'html'),
            ])


    def test_declaration_bad(self):

        # verify the lenient version of sgmllib's declaration parsing

        # there should be no space between '<!' and '--'
        self._test_generator(
            "<html>A<! -- bad comment  -- >B</html>",
            [
            (TAG,    u'html', []),
            (DATA,   u'A'       ),      # verify no extra chars from the bad declaration
            (DATA,   u'B'       ),      # verify no extra chars from the bad declaration
            (ENDTAG, u'html'),
            ])


        # this <! header > is seen in some website
        self._test_generator(
            "<html>A<! header >B</html>",
            [
            (TAG,    u'html', []),
            (DATA,   u'A'       ),      # verify no extra chars from the bad declaration
            (DATA,   u'B'       ),      # verify no extra chars from the bad declaration
            (ENDTAG, u'html'),
            ])


    def test_declaration_incomplete(self):

        # verify that the lenient declaration can handle incompete tags

        doc = " <html>A<!-- bad comment -->B</html>"

        # Note unrelated problem: without the initial space above, there
        # is problem in parsing the incomplete <html>. Investigate?!

        for i in range(1, len(doc)-1):

            chunks = [doc[:i], doc[i:]]
            #print chunks
            fp = ChunkedStringIO(chunks)
            tokens = hpp.generate_tokens(fp)

            self._test_generator1(
                tokens,
                [
                (TAG,    u'html', []),
                (DATA,   u'A'       ),
                (DATA,   u'B'       ),
                (ENDTAG, u'html'),
                ])


    def test_xml_CDATA(self):
        # test use of XML's CDATA, not a standard for HTML?
        self._test_generator(
            "<html>A<![CDATA[something <crazy> & <bad/> here]]>B</html>",
            [
            (TAG,    u'html', []),
            (DATA,   u'A'       ),
            (DATA,   u'something <crazy> & <bad/> here'),
            (DATA,   u'B'       ),
            (ENDTAG, u'html'),
            ])



if __name__ == '__main__':
    unittest.main()