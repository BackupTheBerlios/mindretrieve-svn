"""Usage magic.py filename

From the file header guess the content type by matching it with the
magic data file.
"""

import sys


# Resouces

# http://www.garykessler.net/library/file_sigs.html

# PNG - http://www.libpng.org/pub/png/spec/1.2/PNG-Structure.html

# ico format - http://www.iconolog.net/info/icoFormat.html
#              http://www.iana.org/assignments/media-types/image/vnd.microsoft.icon

# unicode - http://www.unicode.org/faq/utf_bom.html


# Note: We will just include a small number of format that often found
# miscategorized in the web. We don't try to be as exhausive as in the
# Unix type command.
magic_data = [
  ('\x89PNG\x0d\x0a\x1a\x0a', '', 'image/png' ),
  ('GIF87a',                  '', 'image/gif' ),
  ('GIF89a',                  '', 'image/gif' ),
  ('\xff\xd8\xff\xe0',        '', 'image/jpeg'),
  ('\x00\x00\x01\x00\x00\x00', '\xff\xff\xff\xff\x00\xff', 'image/vnd.microsoft.icon'),

# BOM may hint as unicode text. But can't guess subtype like text/html
#  ('\xFE\xFF',                '', 'text/plain'),  # UTF-16 BOM, big-endian
#  ('\xFF\xFE',                '', 'text/plain'),  # UTF-16 BOM, little-endian
#  ('\EF\xBB\xBF',             '', 'text/plain'),  # UTF-8 BOM

]

def guess_type(data):
    for magic, mask, ctype in magic_data:
        if mask:
            if len(data) < len(magic):
                continue
            for c, mk, mg in zip(data[:len(magic)], mask, magic):
                if ord(c) & ord(mk) != ord(mg):
                    break   # not match
            else:
                return ctype
        else:
            if data.startswith(magic):
                return ctype

    return None


def main(argv):
    if len(argv) <= 1:
        print __doc__
        sys.exit(-1)
    header = file(argv[1],'rb').read(256)
    print 'type:', guess_type(header)


if __name__ == '__main__':
    main(sys.argv)