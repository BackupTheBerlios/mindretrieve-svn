"""
"""

import codecs
import logging
import sys

from minds import weblib
from minds.config import cfg


log = logging.getLogger('wlib.opera')

FOLDER, URL, DASH = range(1,4)


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



def parseRecords(rstream):

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

        elif line == '-':
            yield lineno, DASH, None, None

        else:
            log.warn('Unknown line %s - %s', lineno+1, line)



def load(rstream):

    wlib = weblib.WebLibrary()
    folder_stack = []

    recordParser = parseRecords(rstream)

    for lineno, type, name, attrs in recordParser:

        if type == FOLDER:

            if not attrs.has_key('trashfolder'):

                if not name:
                    log.warn('Invalid name line %s', lineno+1)
                    continue

                label = weblib.Label(name=name)
                try:
                    wlib.addLabel(label)
                except KeyError, e:
                    log.info('line %s - %s', lineno+1, e)
                    # not a problem, just use the existing label
                    label = wlib.getLabel(name)

                folder_stack.append(label)

            else:
                # skipping everything under the trash folder
                trash_count = 1
                for lineno, type, name, attrs in recordParser:
                    if type == FOLDER:
                        trash_count += 1
                        log.info('drop %s', name)
                    elif type == DASH:
                        trash_count -= 1
                        if trash_count == 0:
                            break


        elif type == URL:

            if not name:
                log.warn('Invalid name line %s', lineno+1)
                continue

            labelIds = [label.id for label in folder_stack]

            webpage = weblib.WebPage(
                name        = name,
                url         = attrs.get('url',''),
                description = attrs.get('description',''),
                #comment     = attrs.get('shortname', ''),           # note: space compressed
                labelIds    = labelIds,
                modified    = attrs.get('created',''),
                lastused    = attrs.get('visited',''),
            )
            wlib.addWebPage(webpage)


        elif type == DASH:
            if len(folder_stack) == 0:
                log.warn('Unmatched "-" line %s', lineno+1)
            else:
                folder_stack.pop()

    return wlib


#
#def main(argv):
#
#    if len(argv) < 3:
#        print __doc__
#        sys.exit(-1)
#
#    # load
#    wlib = load(file(argv[1],'rb'))
#
#    # save
#    fp = file(argv[2],'wb')
#    import minds_lib
#    minds_lib.save(fp, wlib)
#    fp.close()
#
#
#if __name__ == '__main__':
#    main(sys.argv)