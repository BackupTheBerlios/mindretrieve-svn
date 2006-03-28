import sys

from minds.config import cfg

engines = None

def getEngines():
    global engines
    if engines != None:
        return engines
    engines = cfg.readObject('search_engine',[
        'id',
        'url',
        'label',
        ],[
        'shortcut',
        'history',
        'method',
        'encoding',
        ])
    return engines


def main(argv):
    from pprint import pprint
    pprint(getEngines())


if __name__ == '__main__':
    main(sys.argv)
