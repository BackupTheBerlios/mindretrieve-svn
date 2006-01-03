"""
"""

import datetime
import codecs
import logging
import sys

from minds.config import cfg
from minds import weblib
from minds.weblib import import_util

log = logging.getLogger('imp.opera')

FOLDER, URL, SEPERATOR, DASH = range(1,5)


def _parse_namevalue(nv):
    """ Return (name, value) in s seperated by '='.
        value is '' if there is no value or no '='.
    """
    lst = [s.strip() for s in nv.split('=',1)]
    return len(lst) == 1 and (lst[0], '') or lst


def _parseAttr(lineReader):
    recname = ''
    attrs = {}
    for lineno, line in lineReader:
        line = line.strip()
        if not line:
            break
        name, value = _parse_namevalue(line)
        name = name.lower().replace(' ','')
        value = value.replace('\x02\x02','\n')      # opera's encoding of \n?
        if name == 'name':
            recname = value
        elif name:
            attrs[name] = value
    return recname, attrs



def iterRecords(rstream):

    reader = codecs.getreader('utf8')(rstream,'replace')
    lineReader = enumerate(reader)

    for lineno, line in lineReader:
        line = line.lower().strip()
        if not line:
            continue

        if line == '#folder':
            name, attrs = _parseAttr(lineReader)
            yield lineno, FOLDER, name, attrs

        elif line == '#url':
            name, attrs = _parseAttr(lineReader)
            yield lineno, URL, name, attrs

        elif line == '#seperator':
            name, attrs = _parseAttr(lineReader)
            yield lineno, SEPERATOR, None, None

        elif line == '-':
            yield lineno, DASH, None, None

        else:
            log.warn('Unknown line %s - %s', lineno+1, line)


def parseFile(fp):
    root_folder = import_util.Folder('')
    folder_stack = [root_folder]

    iterator = iterRecords(fp)

    for lineno, type, name, attrs in iterator:

        if type == FOLDER:
            if attrs.has_key('trashfolder'):
                # skipping everything under the trash folder
                trash_count = 1
                for lineno, type, name, attrs in iterator:
                    if type == FOLDER:
                        trash_count += 1
                        log.info('drop %s', name)
                    elif type == DASH:
                        trash_count -= 1
                        if trash_count == 0:
                            break
                continue

            if not name:
                log.warn('Invalid name line %s', lineno+1)
                continue

            folder = import_util.Folder(name)
            folder_stack[-1].children.append(folder)
            folder_stack.append(folder)

        elif type == URL:
            if not name:
                log.warn('Invalid name line %s', lineno+1)
                continue

            created  = attrs.get('created','')
            created  = import_util._ctime_str_2_iso8601(created)
            # Opera doesn't have modified. Map visited to modified.
            modified = attrs.get('visited','')
            modified = import_util._ctime_str_2_iso8601(modified)

            page = import_util.Bookmark(
                name,
                url         = attrs.get('url',''),
                description = attrs.get('description',''),
                created     = created,
                modified    = modified,
            )
            folder_stack[-1].children.append(page)

        elif type == SEPERATOR:
            pass

        elif type == DASH:
            if len(folder_stack) <= 1:
                raise RuntimeError('Unmatched "-" line: %s' % (lineno+1,))
            else:
                folder_stack.pop()

    return root_folder


def import_bookmark(fp):
    root_folder = parseFile(fp)
    return import_util.import_tree(root_folder)


def main(argv):
    pathname = argv[1]
    fp = file(pathname,'rb')
    import_bookmark(fp)


if __name__ =='__main__':
    sys.stdout = codecs.getwriter('utf8')(sys.stdout,'replace')
    sys.stderr = codecs.getwriter('utf8')(sys.stderr,'replace')
    main(sys.argv)
