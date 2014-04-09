__author__ = 'baohua'

VERSION = "0.2"

import re

from easyovs.log import debug


def get_numstr_after(line, field):
    """
    Return the Number value after given field
    >>> get_numstr_after("abc=99,xx","abc=") == '99'
    True
    """
    result = ''
    r = re.search(field + '\d+', line)
    if r:
        result = r.group(0).replace(field, '').strip()
    return result


def get_str_before(line, ch):
    """
    Fetch the string before a sign
    >>> get_str_before('  abc (xx)','(')=='  abc '
    True
    """
    result = ''
    if ch.startswith('\\') or ch.startswith('(') or ch.startswith(')'):
        _ch = '\%s' % ch
    else:
        _ch = ch
    r = re.search(r'.*%s' % _ch, line)
    if r:
        result = r.group(0).replace(ch, '')
    return result


def get_str_between(line, start, end):
    """
    Fetch the string before a sign
    >>> get_str_between('  abc (xx): he','(',')') == 'xx'
    True
    """
    result = ''
    start, end = r'%s' % start, r'%s' % end
    if not start.startswith('\\') and not start.startswith('(') and not start.startswith(')') \
            and not end.startswith('\\') and not end.startswith('(') and not end.startswith(')'):
        r = re.search(r'%s.*%s' % (start, end), line)
    else:
        r = re.search(r'\%s.*\%s' % (start, end), line)
    if r:
        result = r.group(0).replace(start, '').replace(end, '')
    return result

def fmt_flow_str(raw_str):
    """
    Return a valid flow string or None based on given string.
    >>> fmt_flow_str('  ip udp, proto=2,actions=OUTPUT:2')
    'ip,udp,proto=2 actions=OUTPUT:2'
    >>> fmt_flow_str('  "ip,proto=2 actions=OUTPUT:2,NORMAL,"')
    'ip,proto=2 actions=OUTPUT:2,NORMAL'
    >>> fmt_flow_str(' ip proto=2 actions=OUTPUT:2 NORMAL')
    'ip,proto=2 actions=OUTPUT:2,NORMAL'
    """
    if 'actions=' not in raw_str:
        debug(raw_str)
        return None
    fmt_str = raw_str.replace('"', '').replace("'", "").strip()
    i = fmt_str.index('actions=')
    actions = fmt_str[i:].strip(',').replace(',', ' ').split()
    match = fmt_str[:i].strip(',').replace(',', ' ').split()
    if not match or not actions:
        debug(match)
        debug(actions)
        return None
    match = ','.join(match)
    actions = ','.join(actions)
    flow = match + ' ' + actions
    return flow

def color_str(color, raw_str):
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
    return "%s%s\x1B[0m" % (color, raw_str)


if __name__ == '__main__':
    import doctest

    doctest.testmod()
