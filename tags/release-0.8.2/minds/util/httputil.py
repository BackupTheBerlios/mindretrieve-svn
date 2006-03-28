"""Utilities to parse URL and safely convert them into filename.
Some built on top of the urlparse module.

"""

import urlparse


# Below is just a guideline from RFC 1034. Any more authoritative
# specification for domain name syntax? Any update? Unicode? Some domain
# name actually starts with digit

# ------------------------------------------------------------------------
#
# RFC 1034 DOMAIN NAMES - CONCEPTS AND FACILITIES
# 3.5 Preferred name syntax
#
# ...
#
# <domain> 	::=	<subdomain> | " "
# <subdomain> 	::=	<label> | <subdomain> "." <label>
# <label> 	::=	<letter> [ [ <ldh-str> ] <let-dig> ]
# <ldh-str> 	::=	<let-dig-hyp> | <let-dig-hyp> <ldh-str>
# <let-dig-hyp> 	::=	<let-dig> | "-"
# <let-dig> 	::=	<letter> | <digit>
# <letter> 	::=	any one of the 52 alphabetic characters A through Z in
#                 upper case and a through z in lower case
# <digit> 	::=	any one of the ten digits 0 through 9
#
# Note that while upper and lower case letters are allowed in domain
# names, no significance is attached to the case. That is, two names with
# the same spelling but different case are to be treated as if identical.
#
# The labels must follow the rules for ARPANET host names. They must start
# with a letter, end with a letter or digit, and have as interior
# characters only letters, digits, and hyphen. There are also some
# restrictions on the length. Labels must be 63 characters or less.
#
# For example, the following strings identify hosts in the Internet:
#
#   A.ISI.EDU 	XX.LCS.MIT.EDU 	SRI-NIC.ARPA
#
# ------------------------------------------------------------------------

# Other resources
#   RFC - 3490 Internationalizing Domain Names in Applications (IDNA)
#   http://www.ietf.org/internet-drafts/draft-duerst-iri-09.txt
#   http://www.xml.com/pub/a/2003/05/07/deviant.html



def urlsplit(url):
    """ Extend on urlparse.urlsplit() by further parsing the
        network location into userinfo and host.
        @returns scheme, userinfo, host, path, query, frag
    """
    scheme, netloc, path, query, frag = urlparse.urlsplit(url)
    if '@' in netloc:
        userinfo, host = netloc.split('@',1)
    else:
        userinfo, host = '', netloc
    return scheme, userinfo, host, path, query, frag


# todo: do parsing once, use the smae parts from proxyhandler to prevent different intrepretation
def canonicalize(url):
    """ Canonicalize an url """

    # 1. Convert host to lower case
    # 2. Do not include port number for port 80
    # 3. normalize '.' and '..' parts
    # 4. drop userinfo
    # 5. drop fragment
    # 6. url decode. (not doing because it cannot be used in request anymore.)
    scheme, userinfo, host, path, query, frag = urlsplit(url)

    host = host.lower()
    if host.endswith(':80'):        # todo: what if there are 2 or more colons?
        host = host[:-3]

    pparts = path.split('/')        # todo: make sure path start with '/'
    i = 0
    while i < len(pparts):
        if pparts[i] == '.':
            del pparts[i]
        elif pparts[i] == '..':
            if i > 1:               # note: pparts[0] is always the '' before the initial '/'. Never pop it.
                del pparts[i-1:i+1]
                i -= 1
            else:
                del pparts[i]
        else:
            i += 1

    if len(pparts) > 1:
        path = '/'.join(pparts)
    else:
        path = '/'

    return urlparse.urlunsplit((scheme, host, path, query, None))



#MAX_FILENAME = 128
#VALID_CHAR = string.ascii_lowercase + '0123456789-.'
#
#
#def make_filename(host):
#    """ Convert host name into filename.
#        This should be a 1-1 and unique mapping.
#    """
#    host,port = host.lower(),''
#
#    # parse port
#    if ':' in host:
#        host,port = host.split(':')
#        if not port.isdigit() or len(port) > 5:  # '' is also invalid
#            raise SyntaxError, 'Invalid port in host=[' + host +']'
#    if port == '80':
#        port = ''
#
#    # validate and encode host into filename
#    filename = host
#    for c in host:
#        if c not in VALID_CHAR:
#            filename = _encode_host(host)
#            break
#
#    if port:
#        filename = filename + '__' + port
#
#    if len(filename) > MAX_FILENAME:
#        raise SyntaxError, 'Filename exceed %d chars: %s' % (MAX_FILENAME, filename)
#
#    return filename
#
#
#
#def _encode_host(host):
#    """ encode characters outside valid set with %XX """
#
#    l = list(host)
#    for i, c in enumerate(l):
#        if c not in VALID_CHAR:
#            if c == '%':
#                l[i] = '%%'
#            else:
#                l[i] = '%%%2X' % ord(c)
#    return ''.join(l)
#


def abbreviate_ctype(ctype):
    """ Reverse mapping from content-type to 5 char file extension.
        Abbreviate it if it is an unknown type.
    """

    ctype = ctype.split(';',1)[0].strip().lower()
    if not ctype: return ctype
    ext = mime_map.get(ctype,'')
    if ext: return ext

    # a type we don't know yet, abbreviate it
    parts = ctype.split('/',1)
    parts.append('')
    parts[1] = parts[1].lstrip('x-')
    remove_vowel = lambda s: s[0:1] + ''.join([ch for ch in s[1:] if ch not in 'aeiou'])
    parts = map(remove_vowel, parts)
    ext = parts[0][:3] + '/' + parts[1]
    ext = ext[:5]
    mime_map[ctype] = ext
    return ext



# a reverse content-type to extension mapping adapted from minetypes.types_map
mime_map = {
    'application/excel'                    : 'xls'  ,
    'application/msword'                   : 'doc'  ,
    'application/octet-stream'             : 'bin'  ,
    'application/oda'                      : 'oda'  ,
    'application/pdf'                      : 'pdf'  ,
    'application/pkcs7-mime'               : 'p7c'  ,
    'application/postscript'               : 'ps'   ,
    'application/vnd.ms-excel'             : 'xls'  ,
    'application/vnd.ms-powerpoint'        : 'ppt'  ,
    'application/x-bcpio'                  : 'bcpio',
    'application/x-cdf'                    : 'cdf'  ,
    'application/x-cpio'                   : 'cpio' ,
    'application/x-csh'                    : 'csh'  ,
    'application/x-dvi'                    : 'dvi'  ,
    'application/x-gtar'                   : 'gtar' ,
    'application/x-hdf'                    : 'hdf'  ,
    'application/x-javascript'             : 'js'   ,
    'application/x-latex'                  : 'latex',
    'application/x-mif'                    : 'mif'  ,
    'application/x-netcdf'                 : 'cdf'  ,
    'application/x-pkcs12'                 : 'pfx'  ,
    'application/x-pn-realaudio'           : 'ram'  ,
    'application/x-python-code'            : 'pyc'  ,
    'application/x-sh'                     : 'sh'   ,
    'application/x-shar'                   : 'shar' ,
    'application/x-shockwave-flash'        : 'swf'  ,
    'application/x-sv4cpio'                : 'sv4cp',
    'application/x-sv4crc'                 : 'sv4cr',
    'application/x-tar'                    : 'tar'  ,
    'application/x-tcl'                    : 'tcl'  ,
    'application/x-tex'                    : 'tex'  ,
    'application/x-texinfo'                : 'texi' ,
    'application/x-troff'                  : 'tr'   ,
    'application/x-troff-man'              : 'man'  ,
    'application/x-troff-me'               : 'me'   ,
    'application/x-troff-ms'               : 'ms'   ,
    'application/x-ustar'                  : 'ustar',
    'application/x-wais-source'            : 'src'  ,
    'application/xml'                      : 'rdf'  ,
    'application/zip'                      : 'zip'  ,
    'audio/basic'                          : 'au'   ,
    'audio/mpeg'                           : 'mp3'  ,
    'audio/x-aiff'                         : 'aiff' ,
    'audio/x-pn-realaudio'                 : 'ra'   ,
    'audio/x-wav'                          : 'wav'  ,
    'image/gif'                            : 'gif'  ,
    'image/ief'                            : 'ief'  ,
    'image/jpeg'                           : 'jpeg' ,
    'image/png'                            : 'png'  ,
    'image/tiff'                           : 'tiff' ,
    'image/x-cmu-raster'                   : 'ras'  ,
    'image/x-ms-bmp'                       : 'bmp'  ,
    'image/x-portable-anymap'              : 'pnm'  ,
    'image/x-portable-bitmap'              : 'pbm'  ,
    'image/x-portable-graymap'             : 'pgm'  ,
    'image/x-portable-pixmap'              : 'ppm'  ,
    'image/x-rgb'                          : 'rgb'  ,
    'image/x-xbitmap'                      : 'xbm'  ,
    'image/x-xpixmap'                      : 'xpm'  ,
    'image/x-xwindowdump'                  : 'xwd'  ,
    'message/rfc822'                       : 'eml'  ,
    'text/css'                             : 'css'  ,
    'text/html'                            : 'html' ,
    'text/plain'                           : 'txt'  ,
    'text/richtext'                        : 'rtx'  ,
    'text/tab-separated-values'            : 'tsv'  ,
    'text/x-python'                        : 'py'   ,
    'text/x-setext'                        : 'etx'  ,
    'text/x-sgml'                          : 'sgml' ,
    'text/x-vcard'                         : 'vcf'  ,
    'text/xml'                             : 'xml'  ,
    'video/mpeg'                           : 'mpeg' ,
    'video/quicktime'                      : 'mov'  ,
    'video/x-msvideo'                      : 'avi'  ,
    'video/x-sgi-movie'                    : 'movie',
}


# ----------------------------------------------------------------------
# testing
# ----------------------------------------------------------------------

import unittest

#def test_make_filename(s,result):
#    s1 = make_filename(s)
#    assert result == s1, 'make_filename(%s) expect %s gets %s' % (s, result, s1)
#
#def test_make_filenameX(s):
#    try:
#        r = make_filename(s)
#    except SyntaxError, e:
#        pass
#    else:
#        assert False, 'make_filename(%s) should raise exception' % s
#
#def test():
#    test_make_filename('tung397',           'tung397')
#    test_make_filename('$tung wai-yip.com', '%24tung%20wai-yip.com')
#    test_make_filename('TUNG%WAI.COM:80',   'tung%%wai.com')
#    test_make_filename('tung%wai.com:8080', 'tung%%wai.com__8080')
#
#    test_make_filenameX('%'*(MAX_FILENAME/2+1))
#    test_make_filenameX('tung.wai.com:')
#    test_make_filenameX('tung.wai.com:port')
#    test_make_filenameX('tung.wai.com:123456')
#    test_make_filenameX('tung.wai.com:80 ')

class TestHttputil(unittest.TestCase):

    def test_split(self):
        r = urlsplit('http://host')
        self.assertEqual(r,('http','','host','','',''))

        r = urlsplit('/root?q')
        self.assertEqual(r,('','','','/root','q',''))

        r = urlsplit('http://trick@12.34.56/')
        self.assertEqual(r,('http','trick','12.34.56','/','',''))

        r = urlsplit('http://tung:pass@host/')
        self.assertEqual(r,('http','tung:pass','host','/','',''))

        r = urlsplit('http://userinfo@extra@host/')
        self.assertEqual(r,('http','userinfo','extra@host','/','',''))


    def test_canonicalize(self):
        self.assertEqual(canonicalize('ftp://h/a/b/c'),         'ftp://h/a/b/c')
        self.assertEqual(canonicalize('ftp://HoSt/a/b/c'),      'ftp://host/a/b/c')     # host capitalization
        self.assertEqual(canonicalize('ftp://h:80/'),           'ftp://h/')             # remove port 80
        self.assertEqual(canonicalize('ftp://h:8080/'),         'ftp://h:8080/')        # keep port 8080
        self.assertEqual(canonicalize('ftp://h/a/./b/./c'),     'ftp://h/a/b/c')        # .
        self.assertEqual(canonicalize('ftp://h/a/../b/../c'),   'ftp://h/c')            # ..
        self.assertEqual(canonicalize('ftp://h/a/././b/c'),     'ftp://h/a/b/c')        # consecutive .
        self.assertEqual(canonicalize('ftp://h/a/b/../../c'),   'ftp://h/c')            # consecutive ..
        self.assertEqual(canonicalize('ftp://h/a/../../b/c'),   'ftp://h/b/c')          # .. beyond the root
        self.assertEqual(canonicalize('ftp://h/./a/b'),         'ftp://h/a/b')          # starts with .
        self.assertEqual(canonicalize('ftp://h/../a/b'),        'ftp://h/a/b')          # starts with ..
        self.assertEqual(canonicalize('ftp://h/a/b/.'),         'ftp://h/a/b')          # ends with .
        self.assertEqual(canonicalize('ftp://h/a/b/..'),        'ftp://h/a')            # ends with ..
        self.assertEqual(canonicalize('ftp://h/.'),             'ftp://h/')             # only .
        self.assertEqual(canonicalize('ftp://h/..'),            'ftp://h/')             # only ..
        self.assertEqual(canonicalize('ftp://h//a/b//c/'),      'ftp://h//a/b//c/')     # empty part part


if __name__ == "__main__":
    unittest.main()