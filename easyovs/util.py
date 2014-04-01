__author__ = 'baohua'

VERSION = "0.2"

import re


def fetchFollowingNum(line, field):
    """
    Return the Number value after given field
    >>> fetchFollowingNum("abc=99,xx","abc=") == 99
    True
    """
    result = None
    r = re.search(field + '\d+', line)
    if r:
        result = int(r.group(0).replace(field, ''))
    return result

def fetchValueBefore(line,ch):
    """
    Fetch the string before a sign
    >>> fetchValueBefore('  abc (xx)','(')=='  abc '
    True
    """
    result = None
    ch = r'%s' %ch
    if ch.startswith('\\') or ch.startswith('(') or ch.startswith(')'):
        r = re.search(r'.*\%s' %ch, line)
    else:
        r = re.search(r'.*%s' %ch, line)
    result= r.group(0).replace(ch,'')
    return result


def fetchValueBetween(line,start,end):
    """
    Fetch the string before a sign
    >>> fetchValueBetween('  abc (xx): he','(',')') == 'xx'
    True
    """
    result = None
    start,end = r'%s' %start, r'%s' %end
    if not start.startswith('\\') and not start.startswith('(') and not start.startswith(')')\
    and not end.startswith('\\') and not end.startswith('(') and not end.startswith(')')    :
        r = re.search(r'%s.*%s' %(start,end), line)
    else:
        r = re.search(r'\%s.*\%s' %(start,end), line)
    result= r.group(0).replace(start,'').replace(end,'')
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

