__author__ = 'baohua'

import re


def fetchFieldNum(line, field):
    """
    Return the Number value after given field
    >>> fetchFieldNum("abc=99,xx","abc=") == 99
    True
    """
    result = None
    r = re.search(field + '\d+', line)
    if r:
        result = int(r.group(0).replace(field, ''))
    return result


def colorStr(color, str):
    if color == 'r':
        fore = 31
    elif color == 'g':
        fore = 32
    elif color == 'b':
        fore = 36
    elif color == 'y':
        fore = 33
    else:
        fore = 37
    color = "\x1B[%d;%dm" % (1, fore)
    return "%s %s\x1B[0m" % (color, str)


if __name__ == '__main__':
    import doctest

    doctest.testmod()

