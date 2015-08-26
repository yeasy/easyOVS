__author__ = 'baohua'

from subprocess import PIPE, Popen
from easyovs.bridge_ctrl import find_br_ports
from easyovs.log import debug, error, output, warn
from easyovs.util import color_str
from easyovs.neutron import get_port_id_from_ip
from easyovs.namespaces import NameSpaces


# pkts in source out destination prot target other
_format_str_iptables_rule_ = '\t%-10s%-10s%-20s%-8s%-20s%-6s%-20s%-20s\n'

class IPrule(object):
    """
    represent one rule
    INPUT: rule line splits
    """
    def __init__(self, keys):
        self.keys = keys  # rule keys + flags
        self.len = len(self.keys)
        self.content = {}  # {num:1,...}

    def load(self, rule):
        if not rule:
            return False
        rule_fmt = ' '.join(rule.split())
        segs = rule_fmt.split(' ', self.len - 1)  # have flags or not
        for i in range(len(segs)):
            self.content[self.keys[i]] = segs[i]
        if 'flags' not in self.content:
            self.content['flags'] = ''
        return True

    def show(self):
        r = self.content
        if r['source'] == '0.0.0.0/0':
            r['source'] = '*'
        if r['destination'] == '0.0.0.0/0':
            r['destination'] = '*'
        output(_format_str_iptables_rule_
               % (r['pkts'], r['in'], r['source'], r['out'],
                  r['destination'], r['prot'], r['target'], r['flags']))

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
    def __init__(self, name='filter', ns=None):
        self.name = name
        self.chains = {}
        self.run_cmd = 'iptables --line-numbers -nvL -t %s' % self.name
        self.ns = ns

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
            self.ns = ns
        rules, err = Popen(run_cmd, stdout=PIPE, stderr=PIPE,
                           shell=True).communicate()
        if err:
            error("Failed to run %s, err=%s\n" % (run_cmd, err))
            return
        chains = rules.split('\n\n')
        for chain in chains:  # some chain
            r = chain.splitlines()  # lines of rule
            #if not r:
            #    continue
            title = r[0].split()  # r[0] is the title row
            if title[0] == 'Chain' and title[1] not in self.chains:  # title row
                if 'DROP' in title:
                    self.chains[title[1]] = IPchain(title[1], 'DROP')
                else:
                    self.chains[title[1]] = IPchain(title[1])
            keys = r[1].split()
            keys.append('flags')
            self.chains[title[1]].set_keys(keys)
            self.chains[title[1]].add_rules(r[2:])  # those are real rules

    def show(self, chain=None):
        '''
        Get rules from this table
        :param chain:
        :return:
        '''
        if self.ns:
            output(color_str("===ns=%s, table=%s===\n" % (self.ns,
                                                          self.name), 'r'))
        else:
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
        self.nss = NameSpaces()
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

    def show(self, table='filter', chain=None, ns=None):
        '''
        Show the content.
        :param table: which table to show, None for all
        :param chain: which chain to show, None for all.
        :return:
        '''
        debug("Show table=%s, chain=%s, ns=%s\n" % (table, chain, ns))
        self.load(table, chain, ns)
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
        br_port = find_br_ports(port_id)
        if not br_port:
            warn('No br port is found for ip=%s\n' % ip)
            return
        output(color_str('## IP = %s, port = %s\n' % (ip, br_port), 'r'))
        rules_dic = self._query_port_rules(br_port)
        if rules_dic:
            output(color_str( _format_str_iptables_rule_ % (
                'PKTS', 'IN', 'SOURCE', 'OUT', 'DESTINATION', 'PROT',
                'TARGET', 'OTHER'), 'b'))
            for r in rules_dic:
                output(color_str('%s:\n' % r, 'b'))
                self._fmt_show_rules(rules_dic[r])

    def check(self, table='filter', chain='INPUT', ns=None):
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
            return tb.get_chain(chain)

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
        results = {}
        if br_port.startswith('qvo'):  # vm port
            debug('qvo should be vm port\n')
            self.load(table='filter')
            chain_tag = br_port[3:13]
            i_rules = self.get_rules(chain='neutron-openvswi-i' +
                                           chain_tag)
            out = self.get_rules(chain='neutron-openvswi-o' +
                                           chain_tag)
            filter = self.get_rules(chain='neutron-openvswi-s' +
                                           chain_tag)
            if i_rules:
                results['IN'] = i_rules
            if out:
                results['OUT'] = out
            if filter:
                results['SRC_FILTER'] = filter
        else:  # maybe at Network Node
            debug('Should be network function port\n')
            ns = self.nss.find_intf(br_port)
            if not ns:
                warn("port %s not in namespaces\n" % br_port)
            else:
                output('ns=%s\n' % ns)
            self.load(table='nat', ns=ns)
            if br_port.startswith('tap'):  # dhcp
                return None
            elif br_port.startswith('qr-') or br_port.startswith('qg-'):
                pre = self.get_rules(table='nat',
                                     chain='neutron-l3-agent-PREROUTING')
                out = self.get_rules(table='nat',
                                     chain='neutron-l3-agent-OUTPUT')
                float_snat = self.get_rules(table='nat',
                                       chain='neutron-l3-agent-float-snat')
                snat = self.get_rules(table='nat',
                                      chain='neutron-l3-agent-snat')
                if pre:
                    results['PRE'] = pre
                if out:
                    results['OUT'] = out
                if float_snat:
                    results['FLOAT'] = float_snat
                if snat:
                    results['SNAT'] = snat
        return results

    def _fmt_show_rules(self, rule_list):
        """
        Possible columns:
        num   pkts bytes target prot opt in out source destination flags
        """
        for r in rule_list:
            r.show()


if __name__ == '__main__':
    f = IPtables()
    f.load('filter')
    f.show('filter', 'input')
    f.show('filter', 'FORWARD')
