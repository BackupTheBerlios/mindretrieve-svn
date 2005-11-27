import cgi
import logging
import sys
from xml.sax import saxutils

from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import weblib
from minds.weblib import store

log = logging.getLogger('cgi.tagnam')


def main(rfile, wfile, env):
    wlib = store.getWeblib()
    req = request.Request(rfile, env)
    tags = [weblib.parseTag(wlib, tag_id) for tag_id in req.form.getlist('tags')]
    tags = filter(None, tags)
    if req.method == 'POST':
        doPost(wfile, req, tags)
    elif req.method == 'DELETE':
        doDelete(wfile, req, tags)
    else:
        doShowForm(wfile, req)


def doShowForm(wfile, req):
    wlib = store.getWeblib()
    return_url = request.get_return_url(req)

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
            if b: # should always work
                if not b[3]:
                    b[3] =item.name

    tag_base = [(tag.name.lower(), b) for tag,b in tag_dict.items()]
    tag_base.sort()
    tag_base = [b for name,b in tag_base]
    TagNameRenderer(wfile).output(return_url, [], tag_base)


def doPost(wfile, req, tags):
    wlib = store.getWeblib()
    newName = req.param('newName')
    newTag = weblib.parseTag(wlib, newName)
    log.info('doPost tags %s newName %s newTag %s', ','.join(map(unicode,tags)), newName, newTag)

    for tag in tags:
        if not newTag or (newTag is tag):
            # 1. rename to a non-existant tag, or
            # 2. same name or user has changed character case
            wlib.tag_rename(tag, newName)
            # reinitialize newTag for next round in the loop
            newTag = weblib.parseTag(wlib, newName)
        else:
            wlib.tag_merge_del(tag, newTag)

    wlib.category.compile()

    return_url = request.get_return_url(req)
    response.redirect(wfile, '/weblib/tag_naming?return_url=' + return_url)


def doDelete(wfile, req, tags):
    wlib = store.getWeblib()
    log.info('doDelete tags %s', ','.join(map(unicode,tags)))

    for tag in tags:
        wlib.tag_merge_del(tag)

    wlib.category.compile()

    return_url = request.get_return_url(req)
    response.redirect(wfile, '/weblib/tag_naming?return_url=' + return_url)


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


class TagNameRenderer(response.CGIRenderer):
    TEMPLATE_FILE = 'weblibTagNaming.html'
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
        node.content = '%s (%s)' % (tag_item[1], tag_item[2])
        node.atts['value'] = tag_item[0]


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)
