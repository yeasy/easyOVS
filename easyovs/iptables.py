__author__ = 'baohua'

from subprocess import PIPE, Popen
from easyovs.bridge_ctrl import find_br_ports
from easyovs.log import debug, error, output, warn
from easyovs.util import color_str, find_ns
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
        segs = rule_fmt.split(' ', self.len - 1)
        for i in range(len(segs)):
            self.content[self.keys[i]] = segs[i]
        return True

    def show(self):
        for k in self.keys:
            if k in self.content:
                output("%s " % self.content[k])
        output("\n")

    def get_content(self):
        return self.content


class IPchain(object):
    """
    represent one chain
    """
    def __init__(self, name='INPUT', policy='ACCEPT'):
        self.name = name
        self.rules = []  # list of rule objects
        self.keys = []
        self.policy = policy
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
        '''
        Get a list of rules in this chain, e.g., [{},{},{}]
        :return:
        '''
        return self.rules

    def set_policy(self, policy):
        self.policy = policy

    def set_keys(self, keys):
        self.keys = keys

    def show(self):
        '''
        Print all rules in this chain
        :return:
        '''
        output(color_str("chain=%s, policy=%s\n" % (self.name, self.policy),
                         'b'))
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

    def load(self, chain=None, ns=None):
        '''
        Load chains of this table from the system
        :param chain: which chain to load, None for all
        :param ns: which ns to load, None for root
        :return:
        '''
        if chain:
            run_cmd = self.run_cmd + ' ' + chain
        else:
            run_cmd = self.run_cmd
        if ns:
            run_cmd = 'ip netns exec %s %s' % (ns, run_cmd)
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
                if 'DROP' in segs:
                    self.chains[segs[1]] = IPchain(segs[1], 'DROP')
                else:
                    self.chains[segs[1]] = IPchain(segs[1])
            keys = r[1].split()
            keys.append('flags')
            self.chains[segs[1]].set_keys(keys)
            self.chains[segs[1]].add_rules(r[2:])  # those are real rules

    def show(self, chain=None):
        '''
        Get rules from this table
        :param chain:
        :return:
        '''
        output(color_str("===table=%s===\n" % self.name, 'r'))
        for cn in self.chains:
            if not chain or cn.upper() == chain.upper():
                self.chains[cn].show()

    def get_chain(self, chain='INPUT'):
        '''
        Get some chain handler of this table instance.
        :param chain:
        :return: the chain instance, None if failed
        '''
        return self.chains.get(chain, None)

    def get_rules(self, chain=None):
        '''
        Get rules from this table
        if given chain: [{},{}]
        else: {ch1:[{},{}],ch2:[{},{}]}
        :param chain:
        :return:
        '''
        if not chain:
            return self.chains
        else:
            for cn in self.chains:
                if cn.upper() == chain.upper():
                    self.chains[cn].get_rules()
        return None

    def check(self):
        pass


class IPtables(object):
    """
    represent a iptables object, which can handle the table rules
    """
    def __init__(self):
        self.valid_tables = ['raw', 'nat', 'filter', 'mangle', 'security']
        self.tables = {}
        for tb in self.valid_tables:
            self.tables[tb] = IPtable(tb)

    def get_valid_tables(self):
        return self.valid_tables

    def load(self, table=None, chain=None, ns=None):
        '''
        Load the rules from system.
        If given table name, then only load that table.
        :param table: which table to load, None for all
        :param chain: which chain to load, None for all
        :param ns: which ns to load, None for root
        :return:
        '''
        if table in self.valid_tables:
            self.tables[table].load(chain, ns)
        else:
            for tb in self.valid_tables:
                self.tables[tb].load(chain, ns)

    def show(self, table='filter', chain=None):
        '''
        Show the content.
        :param table: which table to show, None for all
        :param chain: which chain to show, None for all.
        :return:
        '''
        debug("Show table=%s, chain=%s\n" % (table, chain or 'None'))
        if table in self.valid_tables:
            self.tables[table].show(chain)

    def vm(self, ip):
        '''
        list vm related rules
        :param ip: vm ip
        :return:
        '''
        debug("Try to show vm rules, ip=%s\n" % ip)
        port_id = get_port_id_from_ip(ip)
        debug('The port id is %s\n' % port_id)
        if not port_id:
            warn('No port id is found for ip=%s\n' % ip)
            return
        output(color_str('## IP = %s, port = %s\n' % (ip, port_id), 'r'))
        br_port = find_br_ports(port_id)
        if not br_port:
            warn('No br port is found for ip=%s\n' % ip)
            return
        debug('The br port is %s\n' % br_port)
        rules_dic = self._query_port_rules(br_port)
        if rules_dic:
            output(color_str( _format_str_iptables_rule_ % (
                'PKTS', 'SOURCE', 'DESTINATION', 'PROT', 'OTHER'), 'b'))
            for r in rules_dic:
                if rules_dic[r]:
                    output('%s:\n' % r)
                    self._fmt_show_rules(rules_dic[r])

    def check(self, table='filter', chain='INPUT'):
        pass

    def get_table(self, table='filter'):
        '''
        Get some table handler of this ipt instance.
        :param table:
        :return: the table instance, None if failed
        '''
        return self.tables.get(table, None)

    def get_chain(self, table='filter', chain='INPUT'):
        '''
        Get some table handler of this ipt instance.
        :param table:
        :return: the table instance, None if failed
        '''
        tb = self.tables.get(table, None)
        if tb:
            return tb.get_chain(table, chain)

    def get_rules(self, table='filter', chain='INPUT'):
        '''
        Get the rule list of a given chain
        :param table:
        :param chain:
        :return: [{},{}]
        '''
        ch = self.get_chain(table, chain)
        if ch:
            return ch.get_rules()
        else:
            return None

    def _query_port_rules(self, br_port):
        """
        Return the dict of the related security rules on a given port.
        {
        'NAME':[iptables rules],
        }
        will load rules first
        """
        if br_port.startswith('qvo'):  # vm port
            debug('qvo should be vm port\n')
            self.load(table='filter')
            chain_tag = br_port[3:13]
            i_rules = self.get_rules(chain='neutron-openvswi-i' +
                                           chain_tag)
            o_rules = self.get_rules(chain='neutron-openvswi-o' +
                                           chain_tag)
            s_rules = self.get_rules(chain='neutron-openvswi-s' +
                                           chain_tag)
            return {'IN': i_rules, 'OUT': o_rules, 'SRC_FILTER': s_rules}
        else:  # maybe at Network Node
            debug('Should be network function port\n')
            ns = find_ns(br_port)
            if not ns:
                debug("port %s not in namespaces\n" % br_port)
            self.load(table='nat', ns=ns)
            if br_port.startswith('tap'):  # dhcp
                return None
            elif br_port.startswith('qr-') or br_port.startswith('qg-'):
                pre = self.get_rules(table='nat',
                                     chain='neutron-l3-agent-PREROUTING')
                out = self.get_rules(table='nat',
                                     chain='neutron-l3-agent-OUTPUT')
                float = self.get_rules(table='nat',
                                       chain='neutron-l3-agent-float-snat')
                snat = self.get_rules(table='nat',
                                      chain='neutron-l3-agent-snat')
                return {'PRE': pre, 'OUT': out, 'FLOAT': float,
                        'SNAT': snat}
            else:
                return None

    def _fmt_show_rules(self, rule_list):
        """
        Possible columns:
        num   pkts bytes target prot opt in out source destination flags
        """
        for r in rule_list:
            if r['target'] is not 'DROP':
                if r['source'] == '0.0.0.0/0':
                    r['source'] = 'all'
                if r['destination'] == '0.0.0.0/0':
                    r['destination'] = 'all'
                output(_format_str_iptables_rule_
                       % (r['pkts'], r['source'],
                          r['destination'], r['prot'], r['flags']))


if __name__ == '__main__':
    f = IPtables()
    f.load('filter')
    f.show('filter', 'input')
    f.show('filter', 'FORWARD')
