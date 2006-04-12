from datetime import datetime

def parse_iso8601_date(s):
    """
    Parse date in iso8601 format. e.g.
        2003-09-15T10:34:54Z
        2003-09-15 10:34:54Z
        2003-09-15T10:34:54
        20030915T103454
        2003-09-15
        20030915
    """
    if s.endswith('Z'):
        s = s[:-1]  # we will treat it as a naive datetime object in UTC
    if ' ' in s:
        ds, ts = s.split(' ',1)
    elif 'T' in s:
        ds, ts = s.split('T',1)
    else:
        ds, ts = s, ''

    # parse date portion
    if len(ds) >= 10 and ds[4] == '-' and ds[7] == '-':
        ds = ds.replace('-','')
    if len(ds) != 8 or not ds.isdigit():
        raise ValueError('Invalid timestamp - "%s"' % ds)
    y = int(ds[0:4])
    m = int(ds[4:6])
    d = int(ds[6:8])

    # parse time portion
    ts = ts.replace(':','')
    if ts and not ts.isdigit():
        raise ValueError('Invalid timestamp - "%s"' % ts)
    ts = (ts + '000000')[:6]
    hh = int(ts[0:2])
    mm = int(ts[2:4])
    ss = int(ts[4:6])

    return datetime(y,m,d,hh,mm,ss)


def isoformat(d,sep='T'):
    s = d.isoformat(sep)[:19]
    s = s[:19]  # trim the sometimes presence ms
    return s