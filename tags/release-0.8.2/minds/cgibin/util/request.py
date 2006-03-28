import cgi
import urllib

WEBLIB_URL = '/weblib'

"""
URL                         method (default GET)  description
--------------------------------------------------------------------------
weblib                                            query or weblib home page

weblib?tag=xx,yy                                  show tag

weblib?query=xx&tag=yy                            search xx

weblib/load                                       [temporary?]

weblib/save                                       [temporary?]


[Resources/webpage]
weblib/_                    GET                   new entry
                            PUT

weblib/%id                  GET, same as form?    entry %id
                            PUT
                            DELETE

weblib/%id/form                                   form for entry %id

weblib/%id/snapshot

weblib/%id/snapshot?cid=

weblib/%id/go;http://xyz                          Redirect to page              <-- (migrate to /url?)

weblib/%id/url#file:///c:/acb                     Launch the (file) URL
                                                  note: the fragment is only for
                                                  user's info. Not sent to server

[tag]
weblib/@%tid                GET (not supported)   tag %id

weblib/@%tid?               POST                  change tag setting
    category_collapse=on/off

"""

class Request(object):

    def __init__(self, rfile, env, encoding='utf8'):
        self.env = env
        self.encoding = encoding
        self.form = cgi.FieldStorage(fp=rfile, environ=env, keep_blank_values=1)

        # the HTTP method
        self.method = env.get('REQUEST_METHOD','GET')
        # allow form parameter to override method
        self.method = self.param('method') or self.method
        self.method = self.method.upper()


    def param(self, name, default=''):
        """ a shorthand for getfirst(). Unicode support."""
        value = self.form.getfirst(name,default)
        if hasattr(value,'decode'):
            value = value.decode(self.encoding)
        return value


class WeblibRequest(Request):

    def __init__(self, rfile, env, encoding='utf8'):
        Request.__init__(self, rfile, env, encoding)

        # parse rid, tid and path for the /weblib URI scheme
        self.rid = None
        self.tid = None
        self.path = env.get('PATH_INFO', '').lstrip('/')

        # try to interpret path as 'id/path'
        # if match, strip the id part from path
        components = self.path.split('/',1)      # a/b/c -> ['a','b/c']
        components.append('')                    # pad it to at least 2 elements
        base = components[0]
        if base == '_':
            self.rid = -1
            self.path = components[1]
        elif base.startswith('@'):
            try:
                self.tid = int(base[1:])
                self.path = components[1]
            except ValueError:
                pass
        elif base[0:1].isdigit():
            try:
                self.rid = int(base)
                self.path = components[1]
            except ValueError:
                pass


    def __str__(self):
        # build string representation of param list
        plst = []
        for k in self.form.keys():
            v = self.form.getfirst(k,'')
            try:
                v = v.decode(self.encoding)
            except UnicodeDecodeError:
                v = v.encode('string_escape').decode('ascii')
            plst.append(u'%s=%s' % (k,v))
        params = ','.join(plst)

        return 'method %s rid=%s tid=%s path=%s param (%s)' % (
            self.method,
            self.rid,
            self.tid,
            self.env.get('PATH_INFO', ''),
            params,
        )


def weblib_url():
    return '%s' % WEBLIB_URL


def rid_url(id):
    return '%s/%s' % (WEBLIB_URL, id)


def go_url(item):
    return '%s/%s/go;%s' % (WEBLIB_URL, item.id, item.url)


def tag_url(tags):
    if hasattr(tags,'encode'):##??
        qs = unicode(tags)
    else:
        qs = u','.join(map(unicode, tags))
    qs = urllib.quote_plus(qs.encode('utf8'))
    return '%s?tag=%s' % (WEBLIB_URL, qs)

