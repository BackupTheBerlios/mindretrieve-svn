import cgi
import urllib

WEBLIB_URL = '/weblib'

"""
URL                         description             method (default GET)
------------------------------------------------------------------------------
weblib                      show home page

weblib?tag=xx,yy            show tag

weblib?query=xx&tag=yy      search xx

weblib/_                    new entry               GET 
                                                    PUT

weblib/%id                  entry %id               GET, same as form?
                                                    PUT 
                                                    DELETE

weblib/%id/form             form for entry %id

weblib/%id/cache
weblib/%id/cache?cid=

weblib/%id/go;http://xyz    Redirect to page
"""

def parseURL(rfile, env):
    """
    Parse the input request base on the URL scheme.
    @return 
        method - HTTP method (auxilliary way by the method parameter)
        form - cgi.FieldStorage
        rid - resource id, -1 for new, None for n/a
        rid_path - if rid is define, the path follows rid
    """  
    form = cgi.FieldStorage(fp=rfile, environ=env)

    # the HTTP method
    method = env.get('REQUEST_METHOD','GET')
    # allow form parameter to override method
    method = form.getfirst('method') or method
    method = method.upper()

    # parse resource id and rid_path
    rid = None
    rid_path = None
    resources = env.get('PATH_INFO', '').lstrip('/').split('/',1)
    resource = resources[0]
    if resource == '_':
        rid = -1
    else:
        try:
            rid = int(resource)
        except ValueError: 
            pass
    if len(resources) > 1:
        rid_path = resources[1]

    return method, form, rid, rid_path


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

