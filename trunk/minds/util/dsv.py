"""Usage: dsv.py filename

DSV parsing library. Run from command line for a quick view of a DSV data file.
"""

import codecs, string, sys

class RowObject(object):
    """ Access a row as a sequence or using attributes name defined in the headers. """

    def __init__(self, headers, fields):
        """ headers is a dict mapping field name to an index. It can be empty.
            fields is the sequence of fields.
        """
        self.headers = headers
        self.fields = fields
        if len(fields) < len(headers):
            # note fields is not altered
            self.fields = self.fields + [''] * (len(headers) - len(self.fields))

    def __len__(self):
        return len(self.fields)

    def __getitem__(self, key):
        return self.fields[key]

    def __getattr__(self, name):
        if not self.headers.has_key(name):
            raise AttributeError, name
        return self.fields[self.headers[name]]

    def __repr__(self):
        return str(self.fields)


#def parse(reader, start_line=1, HEADER_ROW=True, STRIP=True):
#    """ This is the main function to open a DSV file.
#        It generates lineno and a RowObject for each record.
#    """
#
#    # map header name to 0 based column index
#    headers = {}
#    for lineno, line in enumerate(reader):
#        line = line.rstrip()
#        if not line or line.startswith('#'):
#            continue
#        if HEADER_ROW and not headers:
#            headers = parse_header(lineno+1, line)
#            headers = dict(zip(headers, range(len(headers))))
#        else:
#            fields = decode_fields(line)
#            if STRIP:
#                fields = map(string.strip, fields)
#            yield lineno+start_line, RowObject(headers,fields)


def parse_header(lineno, s):
    fields = map(string.strip, decode_fields(s))
    if not fields or filter(None, fields) != fields:
        raise ValueError, 'Header row must contain non-empty field names [line %s]: %s' % (lineno, s)
    fields = map(string.lower, fields)
    return fields


def decode_fields(s):
    """ Decode a DSV line. Returns a sequence of fields. """

    result = []
    current = []

    last=0
    i=0
    while i < len(s):
        if s[i] == '\\':
            current.append(s[last:i])
            i = i+1 # will increment again
            if s[i:i+1] == 'n':
                current.append('\n')
                last = i+1
            elif s[i:i+1] == 'r':
                current.append('\r')
                last = i+1
            else:
                last = i        # will add the char after \ as is
        elif s[i] == '|':
            if current:
                current.append(s[last:i])
                result.append(''.join(current))
                current = []
            else:
                result.append(s[last:i])
            last = i+1
        i += 1

    if current:
        current.append(s[last:i])
        result.append(''.join(current))
        current = []
    else:
        result.append(s[last:i])

    return result


def encode_fields(seq):
    """ Encode a sequence of fields into a DSV line """
    lst = []
    for s in seq:
        s = s.replace('\\', '\\\\')
        s = s.replace('|' , '\\|')
        s = s.replace('\n', '\\n')
        s = s.replace('\r', '\\r')
        lst.append(s)
    return '|'.join(lst)


def main(argv):
    """ quick view/sample code """
    if len(argv) <= 1:
        print __doc__
        sys.exit(-1)

    out = codecs.getwriter('ascii')(sys.stdout,'replace')

    fp = file(argv[1], 'rb')
    for recno, (lineno, fields) in enumerate(parse(fp)):
        if recno == 0:
            print fields.headers
            print '-'*72
        print >>out, '%5d (%d) %s' % (lineno, len(fields), str(fields))
        if lineno % 50 == 49:
            raw_input('>>Press enter to continue')


if __name__ == '__main__':
    main(sys.argv)
