def isSubset(a,b):
    """ return if a is a subset of b; a and b are ordered list. """
    if len(a) == 0:
        return True

    i = 0
    for k in b:
        if a[i] == k:
            i += 1
            if i >= len(a):
                return True
    return False


def diff(a,b):
    """ return a-b """
    d = []
    for k in a:
        if k not in b:
            d.append(k)
    return d
