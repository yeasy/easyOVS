__author__ = 'baohua'

from subprocess import PIPE, Popen
from easyovs.log import output

from easyovs.neutron import get_port_id_from_ip

_format_str_iptables_rule_ = '%8s\t%-16s%-16s%-6s%-20s\n'  # pkts source destination prot other


def show_iptables_rules(ips):
    """
    Show the iptables rules of given vm ips.
    """
    for ip in ips.replace(',', ' ').split():
        port_id = get_port_id_from_ip(ip)
        if not port_id:
            output('No instance with ip %s exists.\n' % ip)
            continue
        port_id = 'qvo' + port_id[:10]
        output('## IP = %s, port = %s\n' % (ip, port_id))
        output(_format_str_iptables_rule_ % ('PKTS', 'SOURCE', 'DESTINATION', 'PROT', 'OTHER'))
        in_rule_list, out_rule_list, s_rule_list = get_iptables_rules(port_id)
        if in_rule_list:
            output('#IN:\n')
            fmt_show_rules(in_rule_list)
        if out_rule_list:
            output('#OUT:\n')
            fmt_show_rules(out_rule_list)
        if s_rule_list:
            output('#SRC_FILTER:\n')
            fmt_show_rules(s_rule_list)


def get_iptables_rules(port_id):
    """
    Return the related security rules on a given port.
    """
    if port_id.startswith('tap') or port_id.startswith('qvo'):
        port_id_used = port_id[3:13]
    else:
        port_id_used = port_id[:10]
    try:
        in_rules = Popen('iptables --line-numbers -nvL %s' % 'neutron-openvswi-i'+port_id_used,
                         stdout=PIPE, stderr=PIPE, shell=True).stdout.read()
        out_rules = Popen('iptables --line-numbers -nvL %s' % 'neutron-openvswi-o'+port_id_used,
                         stdout=PIPE, stderr=PIPE, shell=True).stdout.read()
        s_rules = Popen('iptables --line-numbers -nvL %s' % 'neutron-openvswi-s'+port_id_used,
                          stdout=PIPE, stderr=PIPE, shell=True).stdout.read()
    except Exception:
        return None
    in_rule_list = convert_iptables_rules(in_rules)
    out_rule_list = convert_iptables_rules(out_rules)
    s_rule_list = convert_iptables_rules(s_rules)
    return in_rule_list, out_rule_list, s_rule_list


def convert_iptables_rules(rules):
    """
    Return a list containing the information of the iptables rules.
    An entry would look like
    {'num':1,
    'pkts':20,
    'bytes':20480,
    'target':'DROP',
    'prot':'all',
    'opt':'--',
    'in':'*',
    'out''*':,
    'source':'0.0.0.0/0',
    'destination':'0.0.0.0/0',
    'other':'state RELATED,ESTABLISHED'
    }
    """
    result = []
    if not rules:
        return None
    rule_list = rules.strip('\n').split('\n')
    if len(rule_list) < 3:
        return None
    keys = rule_list[1].split()
    len_key = len(keys)
    rows = rule_list[2:]
    for l in rows:
        r, d = l.split(), {}
        for i in range(len_key):
            d[keys[i]] = r[i]
        d['other'] = ' '.join(r[len_key:])
        result.append(d)
    if result:
        return result


def fmt_show_rules(rule_list):
    """
    Possible columns:
    num   pkts bytes target     prot opt in     out     source        destination   other
    """
    for r in rule_list:
        if r['target'] == 'RETURN':
            if r['source'] == '0.0.0.0/0':
                r['source'] = 'all'
            if r['destination'] == '0.0.0.0/0':
                r['destination'] = 'all'
            output(_format_str_iptables_rule_ % (r['pkts'], r['source'], r['destination'], r['prot'], r['other']))


if __name__ == '__main__':
    get_iptables_rules('qvo583c7038-d3')
