"""
"""


def render(node, title, config):
    configItems = config.items()
    configItems.sort()
    node.items.repeat( renderDocs, zip(xrange(len(configItems)), configItems))


def renderDocs(node, data):
    i, (name, configItem) = data
    if i % 2 == 1: node.atts['class'] = 'altrow'

    baseLink = 'docreader/%s/' % configItem.name

    bookmarks = configItem.bookmark.items()
    bookmarks.sort()

    # find default bookmark['']
    if len(bookmarks) > 0 and bookmarks[0][0] == '':
        defPath = bookmarks[0][1]
        del bookmarks[0:1]
    else:
        defPath = ''

    if defPath[0:1] == '/':
        defPath = defPath[1:]

    node.doc_field.content = name
    node.doc_field.atts['href'] = baseLink + defPath

    node.bookmark_field.repeat( renderBookmark, bookmarks, baseLink)


def renderBookmark(node, data, baseLink):
    bookmark, path = data
    if path[0:1] == '/':
        path = path[1:]
    node.atts['href'] = baseLink + path
    node.content = bookmark
