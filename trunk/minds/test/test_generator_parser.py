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


class TestParser(unittest.TestCase):

    #def test0(self):
    #    buf = StringIO.StringIO(DOC)
    #    for t in gp.generate_tokens(buf):
    #        print t


    def test_parse(self):

        expect = [
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

            'FINISH',                       # this won't match any token
        ]

        buf = StringIO.StringIO(DOC)
        for t in gp.generate_tokens(buf):
            if t == expect[0]:
                del expect[0]

        self.assertEqual(expect[0], 'FINISH')



    def test_parse_emptytag(self):

        # verify workaround of sgmllib's problem in handling empty tag construct. e.g. <br/>, <hr />
        expect = [
            (gp.TAG,    u'html', []),
            (gp.TAG,    u'br',   []),       # get the start tag
            (gp.TAG,    u'hr',   []),       # get the start tag
            (gp.TAG,    u'p',    []),       # and next tag
            (gp.DATA,   u'!',      ),       # and some text
            (gp.ENDTAG, u'html'),
            'FINISH',                       # this won't match any token
        ]

        buf = StringIO.StringIO("<html><br/><hr /><p>!</html>")
        for t in gp.generate_tokens(buf):
            if t == expect[0]:
                del expect[0]

        self.assertEqual(expect[0], 'FINISH')



if __name__ == '__main__':
    unittest.main()