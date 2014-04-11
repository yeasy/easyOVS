__author__ = 'baohua'

from subprocess import PIPE, Popen
from easyovs.log import output

from easyovs.util import get_port_id_from_ip

_format_str_iptables_rule_ = '%8s\t%-20s%-20s%-6s%-20s\n'  # pkts source destination prot other


def show_iptables_rules(ips):
    """
    Show the iptables rules of given vm ips.
    """
    for ip in ips.replace(',', ' ').split():
        port_id = get_port_id_from_ip(ip)
        if not port_id:
            output('No local addr %s exists.\n' % ip)
            continue
        output('## IP = %s, port = %s\n' % (ip, port_id))
        rules_dic = get_iptables_rules(port_id)
        if rules_dic:
            output(_format_str_iptables_rule_ % ('PKTS', 'SOURCE', 'DESTINATION', 'PROT', 'OTHER'))
            for r in rules_dic:
                if rules_dic[r]:
                    output('%s:\n' % r)
                    fmt_show_rules(rules_dic[r])


def get_iptables_rules(port_id):
    """
    Return the dict of the related security rules on a given port.
    {
    'NAME':[iptables rules],
    }
    """
    if port_id.startswith('qvo'):  # local vm at Computer Node
        port_id_used = port_id[3:13]
        try:
            cmd = 'iptables --line-numbers -vnL'
            in_rules = Popen('%s %s' % (cmd, 'neutron-openvswi-i'+port_id_used),
                             stdout=PIPE, stderr=PIPE, shell=True).stdout.read()
            out_rules = Popen('%s %s' % (cmd, 'neutron-openvswi-o'+port_id_used),
                              stdout=PIPE, stderr=PIPE, shell=True).stdout.read()
            s_rules = Popen('%s %s' % (cmd, 'neutron-openvswi-s'+port_id_used),
                            stdout=PIPE, stderr=PIPE, shell=True).stdout.read()
        except Exception:
            return None
        in_rule_list, out_rule_list, s_rule_list = map(convert_iptables_rules, [in_rules, out_rules, s_rules])
        return {'IN':in_rule_list, 'OUT':out_rule_list, 'SRC_FILTER':s_rule_list}
    else:  # maybe at Network Node
        in_ns = ''
        ns_list, error = Popen('ip netns list', stdout=PIPE, stderr=PIPE, shell=True).communicate()
        if error:
            return None
        ns_list = ns_list.strip('\n').split('\n')
        for ns in ns_list:  # qrouter-03266ec4-a03b-41b2-897b-c18ae3279933
            if Popen('ip netns exec %s ip addr | grep %s' % (ns, port_id), stdout=PIPE,
                     stderr=PIPE, shell=True) .communicate()[0]:
                in_ns = ns
                break
        if not in_ns:
            return None
        if port_id.startswith('tap'):  # dhcp
            return None
        elif port_id.startswith('qr-') or port_id.startswith('qg-'):  # router
                cmd = 'ip netns exec %s iptables --line-numbers -t nat -vnL' % in_ns
                pre_rules = Popen('%s %s' %(cmd, 'neutron-l3-agent-PREROUTING'),
                                  stdout=PIPE, stderr=PIPE, shell=True).stdout.read()
                out_rules = Popen('%s %s' %(cmd, 'neutron-l3-agent-OUTPUT'),
                                  stdout=PIPE, stderr=PIPE, shell=True).stdout.read()
                float_rules = Popen('%s %s' %(cmd, 'neutron-l3-agent-float-snat'),
                                  stdout=PIPE, stderr=PIPE, shell=True).stdout.read()
                snat_rules = Popen('%s %s' %(cmd, 'neutron-l3-agent-snat'),
                                    stdout=PIPE, stderr=PIPE, shell=True).stdout.read()
                pre_rule_list, out_rule_list, float_rule_list, snat_rule_list = \
                    map(convert_iptables_rules, [pre_rules, out_rules, float_rules, snat_rules])
                return {'PRE': pre_rule_list, 'OUT': out_rule_list,
                        'FLOAT': float_rule_list, 'SNAT': snat_rule_list}
        else:
            return None


def convert_iptables_rules(rules):
    """
    Return a list containing the information of the iptables rules.
    Would look like
    [
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
    ]
    """
    result = []
    if not rules:
        return result
    rule_list = rules.strip('\n').split('\n')
    if len(rule_list) < 3:
        return result
    keys = rule_list[1].split()
    len_key = len(keys)
    rows = rule_list[2:]
    for l in rows:
        r, d = l.split(), {}
        for i in range(len_key):
            d[keys[i]] = r[i]
        d['other'] = ' '.join(r[len_key:])
        result.append(d)
    return result


def fmt_show_rules(rule_list):
    """
    Possible columns:
    num   pkts bytes target     prot opt in     out     source        destination   other
    """
    for r in rule_list:
        if r['target'] is not 'DROP':
            if r['source'] == '0.0.0.0/0':
                r['source'] = 'all'
            if r['destination'] == '0.0.0.0/0':
                r['destination'] = 'all'
            output(_format_str_iptables_rule_ % (r['pkts'], r['source'], r['destination'], r['prot'], r['other']))


if __name__ == '__main__':
    get_iptables_rules('qvo583c7038-d3')