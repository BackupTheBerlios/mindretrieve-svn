import cgi
import logging
import sys
from xml.sax import saxutils

from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import store

log = logging.getLogger('cgi.categry')

def main(rfile, wfile, env):
    method, form, _, _ = request.parseURL(rfile, env)
    if method == 'POST':
        doPost(wfile, env, form)
    else:
        doShowForm(wfile, env, form)


def doShowForm(wfile, env, form):
    wlib = store.getMainBm()
    return_url = request.get_return_url(env, form)

    # build tag_base
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

    # find uncategorized
    uncategorized = [(
                        unicode(tag).lower(),
                        u'%s (%s)' % (unicode(tag), tag.rel.num_item),
                     ) for tag in wlib.uncategorized]
    uncategorized.sort()
    uncategorized = [t for l,t in uncategorized]

    CategorizeRenderer(wfile, env, '').output(return_url, [], tag_base, wlib.category_description, uncategorized)


def doPost(wfile, env, form):
    wlib = store.getMainBm()

    # TODO: parse and analyze
    wlib.category_description = form.getfirst('category_description','').decode('utf-8')
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


class CategorizeRenderer(response.CGIRendererHeadnFoot):
    TEMPLATE_FILE = 'weblibCategorize.html'
    """ 2005-10-03
    tem:
        con:header
        con:return_url
        con:category_description
        rep:uncategorized_tag
        con:footer
    """
    def render(self, node, return_url, errors, tag_base, category_description, uncategorized):
        node.return_url .atts['value'] = return_url
        ### TODO: need to encode
        node.tag_base_init.raw = '\n'.join(
            ["tag_base['%s'] = [%s,%s];" % (
                b[1],
                b[2],
                saxutils.quoteattr(_title_format(b[3],b[2])),
                ) for b in tag_base]
            )
        node.category_description.content = category_description
        node.uncategorized_tag.repeat(self.render_uncategorized_tag, uncategorized)


    def render_uncategorized_tag(self, node, item):
        node.content = unicode(item)


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)
