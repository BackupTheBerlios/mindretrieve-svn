import os.path
import StringIO
import unittest

from minds import generator_parser as gp

DOC = u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3c.org/TR/html4/loose.dtd">
<html>
<head>
<title>a title</title>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">
<link rel="stylesheet" href="/main.css" type="text/css">
</head>
<body>
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

    def _test_generator(self, doc, expect):
        fp = StringIO.StringIO(doc)
        tokens = gp.generate_tokens(fp)
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

            (gp.TAG,    u'html', []),       # match some start tag
            (gp.DATA,   u'a title'),        # match some text

            (gp.DATA,   u'gt='),
            (gp.DATA,   u'&gt;'),           # retain &gt;

            (gp.DATA,   u'aring='),
            (gp.DATA,   u'\xe5'),           # lowercase entity ref

            (gp.DATA,   u'Aring='),
            (gp.DATA,   u'\xc5'),           # upper case entity ref

            (gp.DATA,   u'229='),
            (gp.DATA,   u'\u00e5'),         # decimal case character ref

            (gp.DATA,   u'e5='),
            (gp.DATA,   u'\u00e5'),         # hex lower case character ref

            (gp.DATA,   u'E5='),
            (gp.DATA,   u'\u00e5'),         # hex upper case character ref

            (gp.ENDTAG, u'html'),           # match some end tag

            ])



class TestSGMLPatch(BaseTest):

    def test_parse_emptytag(self):

        # verify workaround of sgmllib's problem in handling empty tag construct. e.g. <br/>, <hr />

        self._test_generator(
            "<html><br/><hr /><p>!</html>",
            [
            (gp.TAG,    u'html', []),
            (gp.TAG,    u'br',   []),       # get the start tag
            (gp.TAG,    u'hr',   []),       # get the start tag
            (gp.TAG,    u'p',    []),       # and next tag
            (gp.DATA,   u'!',      ),       # and some text
            (gp.ENDTAG, u'html'),
            ])


    def test_declaration_bad(self):

        # verify the lenient version of sgmllib's declaration parsing

        # there should be no space between '<!' and '--'
        self._test_generator(
            "<html>A<! -- bad comment  -- >B</html>",
            [
            (gp.TAG,    u'html', []),
            (gp.DATA,   u'A'       ),   # verify no extra chars from the bad declaration
            (gp.DATA,   u'B'       ),   # verify no extra chars from the bad declaration
            (gp.ENDTAG, u'html'),
            ])


        # this <! header > is seen in some website
        self._test_generator(
            "<html>A<! header >B</html>",
            [
            (gp.TAG,    u'html', []),
            (gp.DATA,   u'A'       ),   # verify no extra chars from the bad declaration
            (gp.DATA,   u'B'       ),   # verify no extra chars from the bad declaration
            (gp.ENDTAG, u'html'),
            ])


    def test_declaration_good(self):

        self._test_generator(
            "<html>A<!-- good comment -->B</html>",
            [
            (gp.TAG,    u'html', []),
            (gp.DATA,   u'A'       ),
            (gp.DATA,   u'B'       ),
            (gp.ENDTAG, u'html'),
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
            tokens = gp.generate_tokens(fp)

            self._test_generator1(
                tokens,
                [
                (gp.TAG,    u'html', []),
                (gp.DATA,   u'A'       ),
                (gp.DATA,   u'B'       ),
                (gp.ENDTAG, u'html'),
                ])



if __name__ == '__main__':
    unittest.main()