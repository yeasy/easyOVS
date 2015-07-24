__author__ = 'baohua'

from subprocess import PIPE, Popen
from easyovs.log import debug, error, output

from easyovs.util import color_str
from easyovs.neutron import get_port_id_from_ip

# pkts source destination prot other
_format_str_iptables_rule_ = '%8s\t%-20s%-20s%-6s%-20s\n'

class IPrule(object):
    """
    represent one rule
    INPUT: rule line splits
    """
    def __init__(self, keys):
        self.keys = keys
        self.len = len(self.keys)
        self.content = {}  # {num:1,...}

    def load(self, rule):
        if not rule:
            return False
        rule_fmt = ' '.join(rule.split())
        segs = rule_fmt.split(' ', self.len-1)
        for i in range(len(segs)):
            self.content[self.keys[i]] = segs[i]
        return True

    def show(self):
        for k in self.keys:
            if k in self.content:
                output("%s " % self.content[k])
        output("\n")


class IPchain(object):
    """
    represent one chain
    """
    def __init__(self, name='INPUT'):
        self.name = name
        self.rules = []  # list of rule objects
        self.keys = []
        #  num pkts bytes target prot opt in out source destination flags

    def add_rules(self, rules):
        '''
        Add list of rules into this chain
        :param rules:
        :return:
        '''
        for r in rules:
            ipr = IPrule(self.keys)
            if ipr.load(r):
                self.rules.append(ipr)

    def get_rules(self):
        return self.rules

    def set_keys(self, keys):
        self.keys = keys

    def show(self):
        '''
        Print all rules in this chain
        :return:
        '''
        output("chain=%s\n" % self.name)
        for r in self.rules:
            r.show()


class IPtable(object):
    """
    represent one table
    """
    def __init__(self, name='filter'):
        self.name = name
        self.chains = {}
        self.run_cmd = 'iptables --line-numbers -nvL -t %s' % self.name

    def load(self, chain=None):
        '''
        Load chains of this table from the system
        :param chain: which chain to load, None for all
        :return:
        '''
        if chain:
            run_cmd = self.run_cmd + ' ' + chain
        else:
            run_cmd = self.run_cmd
        rules, err = Popen(run_cmd, stdout=PIPE, stderr=PIPE,
                           shell=True).communicate()
        if err:
            error("Failed to run %s, err=%s\n" % (run_cmd, err))
            return
        chains = rules.split('\n\n')
        for chain in chains:  # some chain
            r = chain.splitlines()  # lines of rule
            if not r:
                continue
            segs = r[0].split()  # r[0] is the top row
            if segs[0] == 'Chain' and segs[1] not in self.chains:  # no exist
                self.chains[segs[1]] = IPchain(segs[1])
            keys = r[1].split()
            keys.append('flags')
            self.chains[segs[1]].set_keys(keys)
            self.chains[segs[1]].add_rules(r[2:])  # those are real rules

    def show(self, chain=None):
        '''
        Show rules of this table
        :param chain:
        :return:
        '''
        output("table=%s\n" % self.name)
        for cn in self.chains:
            if not chain or cn.upper() == chain.upper():
                self.chains[cn].show()

    def check(self):
        pass


class IPtables(object):
    """
    represent a iptables object, which can handle the table rules
    """
    def __init__(self):
        self.available_tables = ['raw', 'nat', 'filter', 'mangle', 'security']
        self.tables = {}
        for tb in self.available_tables:
            self.tables[tb] = IPtable(tb)

    def get_available_tables(self):
        return self.available_tables

    def load(self, table=None, chain=None):
        '''
        Load the rules from system.
        If given table name, then only load that table.
        :param table: which table to load, None for all
        :param chain: which chain to load, None for all
        :return:
        '''
        if table in self.available_tables:
            self.tables[table].load(chain)
        else:
            for tb in self.available_tables:
                self.tables[tb].load(chain)

    def show(self, table='filter', chain=None):
        '''
        Show the content.
        :param table: which table to show, None for all
        :param chain: which chain to show, None for all.
        :return:
        '''
        debug("Show table=%s, chain=%s\n" % (table, chain))
        if table in self.available_tables:
            self.tables[table].show(chain)

    def check_table(self, table='filter'):
        pass

def show_vm_rules(ips):
    """
    Show the iptables rules of given vm ips.
    """
    for ip in ips.replace(',', ' ').split():
        port_id = get_port_id_from_ip(ip)
        if not port_id:
            output('No local addr %s exists.\n' % ip)
            continue
        output(color_str('r', '## IP = %s, port = %s\n' % (ip, port_id)))
        rules_dic = get_port_rules(port_id)
        if rules_dic:
            output(color_str('b', _format_str_iptables_rule_ % (
                'PKTS',
                'SOURCE',
                'DESTINATION', 'PROT', 'OTHER')))
            for r in rules_dic:
                if rules_dic[r]:
                    output('%s:\n' % r)
                    fmt_show_rules(rules_dic[r])


def get_port_rules(port_id):
    """
    Return the dict of the related security rules on a given port.
    {
    'NAME':[iptables rules],
    }
    """
    if port_id.startswith('qvo'):  # local vm at Computer Node
        port_id_used = port_id[3:13]
        try:
            cmd = 'iptables --line-numbers -nvL'
            in_rules = Popen('%s %s'
                             % (cmd, 'neutron-openvswi-i' + port_id_used),
                             stdout=PIPE, stderr=PIPE, shell=True).stdout.read()
            out_rules = Popen('%s %s'
                              % (cmd, 'neutron-openvswi-o' + port_id_used),
                              stdout=PIPE, stderr=PIPE,
                              shell=True).stdout.read()
            s_rules = Popen('%s %s'
                            % (cmd, 'neutron-openvswi-s' + port_id_used),
                            stdout=PIPE, stderr=PIPE, shell=True).stdout.read()
        except Exception:
            return None
        in_rule_list, out_rule_list, s_rule_list = map(
            convert_iptables_rules, [in_rules, out_rules, s_rules])
        return {'IN': in_rule_list, 'OUT': out_rule_list,
                'SRC_FILTER': s_rule_list}
    else:  # maybe at Network Node
        in_ns = ''
        ns_list, error = Popen('ip netns list', stdout=PIPE, stderr=PIPE,
                               shell=True).communicate()
        if error:
            return None
        ns_list = ns_list.strip('\n').split('\n')
        for ns in ns_list:  # qrouter-03266ec4-a03b-41b2-897b-c18ae3279933
            if Popen('ip netns exec %s ip addr | grep %s' % (ns, port_id),
                     stdout=PIPE, stderr=PIPE, shell=True) .communicate()[0]:
                in_ns = ns
                break
        if not in_ns:
            return None
        if port_id.startswith('tap'):  # dhcp
            return None
        elif port_id.startswith('qr-') or port_id.startswith('qg-'):  # router
            cmd = 'ip netns exec %s iptables --line-numbers -t nat -vnL'\
                  % in_ns
            pre_rules = Popen('%s %s'
                              % (cmd, 'neutron-l3-agent-PREROUTING'),
                              stdout=PIPE, stderr=PIPE,
                              shell=True).stdout.read()
            out_rules = Popen('%s %s'
                              % (cmd, 'neutron-l3-agent-OUTPUT'),
                              stdout=PIPE, stderr=PIPE,
                              shell=True).stdout.read()
            float_rules = Popen('%s %s'
                                % (cmd, 'neutron-l3-agent-float-snat'),
                                stdout=PIPE, stderr=PIPE,
                                shell=True).stdout.read()
            snat_rules = Popen('%s %s'
                               % (cmd, 'neutron-l3-agent-snat'),
                               stdout=PIPE, stderr=PIPE,
                               shell=True).stdout.read()
            pre_rule_list, out_rule_list, float_rule_list, snat_rule_list = \
                map(convert_iptables_rules, [pre_rules, out_rules,
                                             float_rules, snat_rules])
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
    num   pkts bytes target prot opt in out source destination other
    """
    for r in rule_list:
        if r['target'] is not 'DROP':
            if r['source'] == '0.0.0.0/0':
                r['source'] = 'all'
            if r['destination'] == '0.0.0.0/0':
                r['destination'] = 'all'
            output(_format_str_iptables_rule_
                   % (r['pkts'], r['source'],
                      r['destination'], r['prot'], r['other']))


if __name__ == '__main__':
    #get_port_rules('qvo583c7038-d3')
    f = IPtables()
    f.load('filter')
    f.show('filter', 'input')
    f.show('filter', 'FORWARD')
