__author__ = 'baohua'

from subprocess import Popen, PIPE
import re

from easyovs.log import debug, info


def sh(cmd):
    """
    Print a command and send it to the shell
    """
    info(cmd + '\n')
    return Popen(['/bin/sh', '-c', cmd], stdout=PIPE).communicate()[0]


def cleanup():
    """Clean up junk which might be left over from old runs;
    """
    sh('pkill -9 -f "neutron port-list"')

    debug("*** Removing junk from /tmp\n")
    sh('rm -f /tmp/tmp_switch_* /tmp/vlogs* /tmp/*.out /tmp/*.log')

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
    >>> get_numstr_after("abc=19,xx","abc=") == 19
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


def color_str(raw_str, color):
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


def find_ns(key):
    ns_list, err = Popen('ip netns list', stdout=PIPE, stderr=PIPE,
                         shell=True).communicate()
    if err:
        return None
    ns_list = ns_list.splitlines()
    for ns in ns_list:  # qrouter-03266ec4-a03b-41b2-897b-c18ae3279933
        if Popen('ip netns exec %s ip addr | grep %s' % (ns, key),
                 stdout=PIPE, stderr=PIPE,
                 shell=True) .communicate()[0]:
            return ns
    return None


if __name__ == '__main__':
    import doctest
    doctest.testmod()
