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
    req = request.Request(rfile, env)
    if req.method == 'POST':
        doPost(wfile, req)
    else:
        doShowForm(wfile, req)


def doShowForm(wfile, req):
    wlib = store.getMainBm()

    # build tag_base
    tag_dict = dict([
                    (tag, ['@%s' % tag.id,
                           tag.name,
                           tag.num_item,
                           None,
                          ]
                    ) for tag in wlib.tags]
               )

    # fill in first webpage in b[3]
    for item in wlib.webpages:
        for tag in item.tags:
            b = tag_dict.get(tag,None)
            if b: # just in case
                if not b[3]:
                    b[3] = item.name

    tag_base = [(tag.name.lower(), b) for tag,b in tag_dict.items()]
    tag_base.sort()
    tag_base = [b for name,b in tag_base]

    # find uncategorized
    un_list = [(
                unicode(tag).lower(),
                u'%s (%s)' % (unicode(tag), tag.num_item),
               ) for tag in wlib.category.uncategorized]
    un_list.sort()
    uncategorized = [t for l,t in un_list]

    CategorizeRenderer(wfile).output([], tag_base, wlib.category.getDescription(), uncategorized)


def doPost(wfile, req):
    wlib = store.getMainBm()

    # TODO: parse and check for error?
    text = req.param('category_description')
    wlib.category.setDescription(text)
    wlib.category.compile()

    # there is no update of header value. Save the data file.
    wlib.store.save()

    response.redirect(wfile, '/weblib/tag_categorize')


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


class CategorizeRenderer(response.CGIRenderer):
    TEMPLATE_FILE = 'weblibTagCategorize.html'
    """ 2005-10-03
    tem:
        con:header
        con:category_description
        rep:uncategorized_tag
        con:footer
    """
    def render(self, node, errors, tag_base, category_description, uncategorized):
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
