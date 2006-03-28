"""Usage: distillparse.py options [9 digit docid|pathname]

options:
    -r  render in HTML
    -s  strip tags
"""

import os.path
import shutil
import StringIO
import sys

from minds.config import cfg
from minds import distillML
from minds import docarchive

def parseHeader(rfile):
    """ Parse the headers. Position rfile and the beginning of content
        and return meta.
    """
    meta = {}
    line = rfile.readline().rstrip()
    while line:
        if line.find(':') < 0:
            raise IOError('Invalid header line: "%s"' % line)
        name, val = line.split(':',1)
        meta[name.strip().lower()] = val.strip()
        line = rfile.readline().rstrip()
    return meta


def writeHeader(writer, meta):
    writer.write(meta.get('title'      ,''))
    writer.write(u'\n')
    writer.write(meta.get('description',''))
    writer.write(u'\n')
    writer.write(meta.get('keywords'   ,''))
    writer.write(u'\n')


def parseDistillML(rstream, writeHeader=None, bufsize=32768):
    """ Parse distillML (as stored in the archive).
        Build meta data dictionary and strip tags in content.
        @returns meta, content
    """

    import codecs
    reader = codecs.getreader('utf8')(rstream,'replace')

    meta = parseHeader(reader)

    # optionally put meta data at the beginning of content
    buf = StringIO.StringIO()
    if writeHeader:
        writeHeader(buf, meta)

    # parse content
    data = ''
    cpos = 0
    while True:

        if cpos >= len(data):           # data exhausted, read next block
            cpos = 0
            data = reader.read(bufsize)
            if not data:                # exit loop?
                break


        # STATE: not in tag (or not known to be in tag)
        lt = data.find('<', cpos)

        if lt < 0:
            buf.write(data[cpos:])      # no '<', output remain chars in buf
            cpos = len(data)
            continue
        elif lt > cpos:
            buf.write(data[cpos:lt])    # output buf up to the '<'
            cpos = lt
        else:
            pass                        # lt==cpos, i.e. cpos already at '<'


        # STATE: in potential tag, cpos at '<'

        # make sure we have enough character for a possible tag
        if lt + distillML.MAX_OUTPUT_TAG_LEN > len(data):
            data = data[cpos:] + reader.read(bufsize)
            cpos = 0

        for t in distillML.OUTPUT_TAG:
            if data.startswith(t, cpos):
                cpos += len(t)          # recognized tag, drop it and move pass the '>'
                break
        else:
            buf.write(data[cpos])       # no matching tag, output and move pass the '<'
            cpos += 1

    return meta, buf.getvalue()



DISTILLML_VIEW_HEADER = \
"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3c.org/TR/html4/loose.dtd">
<html>
<head>
<title>%(title)s</title>
<link rel='stylesheet' type='text/css' href='distillML.css' />
</head>

<body>
"""

DISTILLML_VIEW_FOOTER = \
"""</body>
</html>
"""

def render(fp, wfile):

    meta = parseHeader(fp)
    uri = meta.get('uri')
    date = meta.get('date', 'no dateZ')
    title = meta.get('title', '') or uri or 'Untitled'
    date = date.replace('T', ' ')[0:-1]
    date += 'Z'                                         # todo: should convert to localtime, for now let people know it is GMT
    title = '%s (%s)' % (title, date)

    wfile.write(DISTILLML_VIEW_HEADER % {'title':title})

    shutil.copyfileobj(fp, wfile)
    wfile.write(DISTILLML_VIEW_FOOTER)


def _render(fp, wfile, next):
    """ A development helper """

    meta = parseHeader(fp)
    uri = meta.get('uri')
    date = meta.get('date', 'no dateZ')
    title = meta.get('title', '') or uri or 'Untitled'
    date = date.replace('T', ' ')[0:-1]
    date += 'Z'                                         # todo: should convert to localtime, for now let people know it is GMT
    title = '%s (%s)' % (title, date)

    wfile.write(DISTILLML_VIEW_HEADER % {'title':title})

    wfile.write('<a href="%s">Next</a><br>\n' % next)

    shutil.copyfileobj(fp, wfile)
    wfile.write(DISTILLML_VIEW_FOOTER)



# ----------------------------------------------------------------------
# Cmdline util/testing

import pprint
def stripTags(rfile, wfile):
    meta, content = parseDistillML(rfile, writeHeader=writeHeader)
    pprint.pprint(meta, wfile)
    print >>wfile
    print >>wfile, content.encode('unicode_escape')


def main(argv):

    if len(argv) < 3:
        print __doc__
        sys.exit(-1)

    option = argv[1]
    path_or_id = argv[2]

    fp = None
    try:
        if os.path.exists(path_or_id):
            fp = file(path_or_id, 'rb')
        else:
            path_or_id = ('000000000' + path_or_id)[-9:]
            fp = docarchive.get_document(path_or_id)

        if option == '-s':
            stripTags(fp, sys.stdout)
        elif option == '-r':
            render(fp, sys.stdout)
        else:
            print __doc__
            sys.exit(-1)

    finally:
        if fp: fp.close()


if __name__ == '__main__':
    main(sys.argv)
