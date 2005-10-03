import cgi
import logging
import sys
from xml.sax import saxutils

from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import store

log = logging.getLogger('cgi.tagname')

def main(rfile, wfile, env):
    method, form, _, _ = request.parseURL(rfile, env)
    if method == 'POST':
        doPost(wfile, env, form)
    else:
        doShowForm(wfile, env, form)


def doShowForm(wfile, env, form):
    wlib = store.getMainBm()
    return_url = request.get_return_url(env, form)
    uncategorized = [(unicode(tag).lower(), unicode(tag)) for tag in wlib.uncategorized]
    uncategorized.sort()
    uncategorized = [t for l,t in uncategorized]
    tag_dict = dict([
                    (tag, ['@%s' % tag.id,
                           tag.name,
                           tag.rel.num_item,
                           None,
                          ]
                    ) for tag in wlib.tags]
               )

    # fill in first webpage in b[3]
    for item in wlib.webpages:
        for tag in item.tags:
            b = tag_dict[tag]
            if b: # just in case
                if not b[3]:
                    b[3] =item.name

    tag_base = [(tag.name.lower(), b) for tag,b in tag_dict.items()]
    tag_base.sort()
    tag_base = [b for name,b in tag_base]
    TagNameRenderer(wfile, env, '').output(return_url, [], tag_base)


def doPost(wfile, env, form):
    wlib = store.getMainBm()

    # TODO: parse and analyze
    wlib.category_description = form.getfirst('category_description').decode('utf-8')

    from minds.util import dsv
    data = dsv.encode_fields(['@0', '', wlib.category_description] + [''] * (10-3))
    print >>sys.stderr, data

    wlib.categorize()

    return_url = request.get_return_url(env, form)
    store.save(wlib)
    response.redirect(wfile, return_url)


# ----------------------------------------------------------------------

_TRIM_TITLE = 50
def _title_format(webpage,count):
    if not webpage:
        return ''
    s = unicode(webpage)
    if count > 1:
        suffix = ',...'
    elif len(s) > _TRIM_TITLE:
        suffix = '...'
    else:
        suffix = ''
    return s[:_TRIM_TITLE] + suffix


class TagNameRenderer(response.CGIRendererHeadnFoot):
    TEMPLATE_FILE = 'weblibTagName.html'
    """ 2005-10-03
    tem:
        con:tag_base_init
        con:header
        con:return_url
        rep:tag
        con:footer
    """
    def render(self, node, return_url, errors, tag_base):
        """
        @param tag_base - list of (tag_id, tag_name, count, a webpage)
        """
        node.return_url .atts['value'] = return_url
        node.tag_base_init.raw = '\n'.join(
            ["tag_base['%s'] = [%s,%s];" % (
                b[0],
                b[2],
                saxutils.quoteattr(_title_format(b[3],b[2])),
                ) for b in tag_base]
            )
        node.tag.repeat(self.render_tag, tag_base)


    def render_tag(self, node, tag_item):
        node.content = tag_item[1]
        node.atts['value'] = tag_item[0]


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)
