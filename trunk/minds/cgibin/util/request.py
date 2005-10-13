import cgi
import urllib

WEBLIB_URL = '/weblib'

"""
URL                         method (default GET)      description
------------------------------------------------------------------------------
weblib                                                query or weblib home page

weblib?tag=xx,yy                                      show tag

weblib?query=xx&tag=yy                                search xx

[Resources/webpage]
weblib/_                    GET                       new entry
                            PUT

weblib/%id                  GET, same as form?        entry %id
                            PUT
                            DELETE

weblib/%id/form                                       form for entry %id

weblib/%id/snapshot

weblib/%id/snapshot?cid=

weblib/%id/go;http://xyz                              Redirect to page

[tag]
weblib/@%tid                GET (not supported)       tag %id

weblib/@%tid?               POST                      change tag setting
    category_collapse=on/off

"""

def parse_weblib_url(rfile, env, keep_blank_values=1):
    """
    Parse the input request base on the weblib URL scheme.
    @return
        method - HTTP method (auxilliary way by the method parameter)
        form - cgi.FieldStorage
        rid - resource id, -1 for new, None for n/a
        tid - tag id or None
        path - rest of path follows rid or tid (without initial '/')
    """
    form = cgi.FieldStorage(fp=rfile, environ=env, keep_blank_values=keep_blank_values)

    # the HTTP method
    method = env.get('REQUEST_METHOD','GET')
    # allow form parameter to override method
    method = form.getfirst('method') or method
    method = method.upper()

    # parse rid, tid and path
    rid = None
    tid = None
    path = ''
    # /a/b/c -> [a,b/c]
    resources = env.get('PATH_INFO', '').lstrip('/').split('/',1)
    resource = resources[0]
    if resource == '_':
        rid = -1
    elif resource.startswith('@'):
        try:
            tid = int(resource[1:])
        except ValueError:
            pass
    else:
        try:
            rid = int(resource)
        except ValueError:
            pass

    if len(resources) > 1:
        path = resources[1]

    return method, form, rid, tid, path


def get_return_url(env, form):
    """ Find what URL to go to when this form is closed? """
    r = form.getfirst('return_url')
    if r: return r
    r = env.get('HTTP_REFERER','')
    if r: return r
    return WEBLIB_URL


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

