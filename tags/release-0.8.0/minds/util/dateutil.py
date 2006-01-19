from datetime import datetime

def parse_iso8601_date(s):
    """ Parse date in iso8601 format e.g. 2003-09-15T10:34:54 and
        returns a datetime object.
    """
    y=m=d=hh=mm=ss=0
    if len(s) not in [10,19,20]:
        raise ValueError('Invalid timestamp length - "%s"' % s)
    if s[4] != '-' or s[7] != '-':
        raise ValueError('Invalid separators - "%s"' % s)
    if len(s) > 10 and (s[13] != ':' or s[16] != ':'):
        raise ValueError('Invalid separators - "%s"' % s)
    try:
        y = int(s[0:4])
        m = int(s[5:7])
        d = int(s[8:10])
        if len(s) >= 19:
            hh = int(s[11:13])
            mm = int(s[14:16])
            ss = int(s[17:19])
    except Exception, e:
        raise ValueError('Invalid timestamp - "%s": %s' % (s, str(e)))
    return datetime(y,m,d,hh,mm,ss)


def isoformat(d,sep='T'):
    s = d.isoformat(sep)[:19]
    s = s[:19]  # trim the sometimes presence ms
    return s