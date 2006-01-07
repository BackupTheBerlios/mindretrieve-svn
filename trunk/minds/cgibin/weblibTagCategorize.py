import cgi
import logging
import sys
from xml.sax import saxutils

from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import store

log = logging.getLogger('cgi.catgry')

def main(rfile, wfile, env):
    req = request.Request(rfile, env)
    if req.method == 'POST':
        doPost(wfile, req)
    else:
        doShowForm(wfile, req)


def doShowForm(wfile, req):
    wlib = store.getWeblib()

    # build tag_base
    wlib.category._countTag()
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
    uncategorized = wlib.category.getUncategorized()
    un_list = [(
                unicode(tag).lower(),
                u'%s (%s)' % (unicode(tag), tag.num_item),
               ) for tag in uncategorized]
    un_list.sort()
    uncategorized = [t for l,t in un_list]

    renderer = CategorizeRenderer(wfile)
    renderer.setLayoutParam('Categorize Tags', '', response.buildBookmarklet(req.env))
    renderer.output([], tag_base, wlib.category.getDescription(), uncategorized)


def doPost(wfile, req):
    wlib = store.getWeblib()

    # TODO: parse and check for error?
    text = req.param('category_description')

    # setDescription() has a quick & dirty way to get rid of illegal characters
    wlib.category.setDescription(text)

    response.redirect(wfile, '/weblib')


# ----------------------------------------------------------------------

_TRIM_TITLE = 50

def _format_tag_base(tag_info):

    encoded_tag_name = response.jsEscapeString(tag_info[1])
    count = tag_info[2]
    if not tag_info[3]:
        encoded_hint = ''
    else:
        hint = unicode(tag_info[3])
        if count > 1:
            suffix = ',...'
        elif len(hint) > _TRIM_TITLE:
            suffix = '...'
        else:
            suffix = ''
        hint = hint[:_TRIM_TITLE] + suffix
        encoded_hint = response.jsEscapeString(hint)

    statement = "tag_base['%s'] = [%s,'%s'];" % (encoded_tag_name, count, encoded_hint)
    return statement


class CategorizeRenderer(response.WeblibLayoutRenderer):

    TEMPLATE_FILE = 'weblibTagCategorize.html'
    """ 2005-10-03
    tem:
        con:header
        con:category_description
        rep:uncategorized_tag
        con:footer
    """
    def render(self, node, errors, tag_base, category_description, uncategorized_tags):
        """
        @param tag_base - list of ('@id', tag name, count, sample webpage title)
        """
        node.tag_base_init.raw = '\n'.join(map(_format_tag_base, tag_base))
        node.category_description.content = category_description
        node.uncategorized_tag.repeat(self.render_uncategorized_tag, uncategorized_tags)


    def render_uncategorized_tag(self, node, tag):
        node.content = unicode(tag)


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)
