__author__ = 'baohua'

from subprocess import Popen, PIPE
import re
import socket
import struct

from easyovs.log import debug, info, warn


def sh(cmd):
    """
    Print a command and send it to the shell
    """
    info(cmd + '\n')
    return Popen(['/bin/sh', '-c', cmd], stdout=PIPE).communicate()[0]


def cleanup():
    """Clean up junk which might be left over from old runs;
    """
    debug("*** Removing junk from /tmp\n")
    sh('rm -f /tmp/*.flows')

    debug("*** Cleanup complete.\n")


def get_numstr_after(line, field):
    """
    Return the Number value in string after given field or ''
    >>> get_numstr_after("abc=99,xx","abc=") == '99'
    True
    """
    result = ''
    r = re.search(field + '\d+', line)
    if r:
        result = r.group(0).replace(field, '').strip()
    return result


def get_num_after(line, field):
    """
    Return the Number value after given field or None
    >>> get_num_after("abc=19,xx","abc=") == 19
    True
    """
    result = get_numstr_after(line, field)
    if result:
        return int(result)
    else:
        return None


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
    if not start.startswith('\\') and not start.startswith('(') and not \
            start.startswith(')') and not end.startswith('\\') and not \
            end.startswith('(') and not end.startswith(')'):
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


def r(raw_str):
    return color_str(raw_str, 'r')


def g(raw_str):
    return color_str(raw_str, 'g')


def b(raw_str):
    return color_str(raw_str, 'b')


def color_str(raw_str, color):
    """
    Render the string with color
    :param raw_str:
    :param color:
    :return:
    """
    if color == 'r':
        fore = 31
    elif color == 'g':
        fore = 32
    elif color == 'y':
        fore = 33
    elif color == 'b':
        fore = 34
    elif color == 'p':
        fore = 35
    elif color == 'light_blue':
        fore = 36
    else:
        fore = 37
    color = "\x1B[%d;%dm" % (1, fore)
    return "%s%s\x1B[0m" % (color, raw_str)


def compress_mac_str(raw_str):
    """
    Compress the show of a redundant mac string.
    >>> compress_mac_str('00:00:02:01:01:02')
    '00:00:02:01:01:02'
    >>> compress_mac_str('00:00:00:01:01:02')
    '00::01:01:02'
    >>> compress_mac_str('00:00:00:01:01:01')
    '00::01:01:01'
    """
    if re.search(r'(\d\d:)\1{2,}', raw_str):
        return re.sub(r'(\d\d:)\1{2,}', r'\1:', raw_str)
    else:
        return raw_str

def get_all_bridges():
    """
    Return a dict of all available bridges, looks like
    {
        'br-int':{
            'Controller':[],
            'fail_mode':'',
            'Port':{
             'qvoxxx': {
                'tag':'1', //tagid
                'type':'internal', //tagid
                },
            }
        },
    }
    """
    brs, br = {}, ''
    cmd = 'ovs-vsctl show'
    result, error = Popen(cmd, stdout=PIPE, stderr=PIPE,
                          shell=True).communicate()
    if error:
        return {}
    for l in result.split('\n'):
        l = l.strip().replace('"', '')
        if l.startswith('Bridge '):
            br = l.lstrip('Bridge ')
            brs[br] = {}
            brs[br]['Controller'] = []
            brs[br]['Port'] = {}
            brs[br]['fail_mode'] = ''
        else:
            if l.startswith('Controller '):
                brs[br]['Controller'].append(l.replace('Controller ', ''))
            elif l.startswith('fail_mode: '):
                brs[br]['fail_mode'] = l.replace('fail_mode: ', '')
            elif l.startswith('Port '):
                phy_port = l.replace('Port ', '')  # e.g., br-eth0
                brs[br]['Port'][phy_port] = {'vlan': '', 'type': ''}
            elif l.startswith('tag: '):
                brs[br]['Port'][phy_port]['vlan'] = l.replace('tag: ', '')
            elif l.startswith('Interface '):
                brs[br]['Port'][phy_port]['intf'] = \
                    l.replace('Interface ', '')
            elif l.startswith('type: '):
                brs[br]['Port'][phy_port]['type'] = l.replace('type: ', '')
    return brs

def makeMask(n):
    "return a mask of n bits as a long integer"
    return (2L<<int(n)-1) - 1

def dottedQuadToNum(ip_str):
    "convert decimal dotted quad string to long integer"
    s = map(lambda x:int(x), ip_str.split('.'))
    return s[3] + s[2] << 8 + s[1] << 16 + s[0] << 24

def networkMask(ip_str, bits):
    """
    '10.0.0.1', '24'
    :param ip_str:
    :param bits:
    :return:
    """
    "Convert a network address to a long integer"
    return dottedQuadToNum(ip_str) & makeMask(bits)

def ipInNetworks(ip_str, networks):
    """
    10.0.0.1 in [10.0.0.0/24, 11.0.0.2/16]
    :param ip_str:
    :param networks:
    :return:
    """
    for n in networks:
        if ipInNetwork(ip_str, n):
            return True
    return False

def ipInNetwork(ip_str, network):
    """
    10.0.0.1 in 10.0.0.0/24
    :param ip_str:
    :param network:
    :return:
    """
    ip_network, mask = network.split('/')
    return  networkMask(ip_str, mask) == networkMask(ip_network, mask)

def fileHasLine(file, line):
    """
    Test if the file content has the line, will ignore the space among it
    :param file:
    :param line:
    :return:
    """
    try:
        f = open(file, 'r')
    except IOError:
        warn(r('Cannot open file', file))
        return False
    line = line.replace(' ','')
    while True:
        lines = f.readlines(1000)
        lines = map(lambda x: x.strip('\n').replace(' ',''), lines)
        if not lines:
            break
        for _line in lines:
            if _line == line:
                return True
    return False

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    print dottedQuadToNum('169.254.31.28')

    fileHasLine('/etc/sysctl.conf', 'net.ipv4.ip_forward=1')
