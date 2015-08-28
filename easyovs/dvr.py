__author__ = 'baohua'

from easyovs.bridge import Bridge
from easyovs.namespaces import NameSpace, NameSpaces
from easyovs.log import error, output, warn
from easyovs.util import r, g, b, networkMask, ipInNetwork, ipInNetworks, \
    fileHasLine, get_all_bridges
from easyovs.bridge import Bridge
from easyovs.iptables import IPtables


class DVR(object):
    """
    DVR configuration
    """
    def __init__(self, node='compute'):
        """
        :param node: on computer node or network node
        """
        self.node = node
        self.br_int = Bridge('br-int')
        self.nss = NameSpaces()

    def check(self, _node=None):
        node = _node or self.node
        if node in 'compute':
            self._compute_node_check()
        elif node in 'network':
            output(b('# Checking DVR on network node\n'))
            self._check_network_node()
        else:
            error('Unknown node type=%s, compute or network?\n' % node)

    def _check_chain_rule_num(self, table, c_name, num):
        """
        Check if the chain has given number of rules.
        :param table: table object
        :param c_name:
        :param num:
        :return:
        """
        output(b('Checking chain rule number: %s...' % c_name))
        c = table.get_chain(c_name)
        if len(c.get_rules()) != num:
            warn(r("Wrong rule number in chain %s\n" % c_name))
            return False
        else:
            output(g('Passed\n'))
            return True

    def _check_chain_has_rule(self, table, c_name, rule):
        """

        :param rule:
        :return: True or False
        """
        output(b('Checking chain rules: %s...' % c_name))
        c = table.get_chain(c_name)
        if not c.has_rule(rule):
            warn(r("Defined rule not in %s\n" % c_name))
            return False
        else:
            output(g('Passed\n'))
            return True

    def _compute_check_nat_rules(self, qr_intfs, rfp_intfs, nat, ns_fip):
        """
        Check three chains rules match with each other
        :param nat: the nat table
        :param ns_fip:
        :return: True or False
        """
        c_name = 'neutron-l3-agent-PREROUTING'
        rule = {'in': 'qr-+', 'source': '*', 'out': '*',
                'destination': '169.254.169.254',
                'target': 'REDIRECT', 'prot': 'tcp',
                'flags': 'tcp dpt:80 redir ports 9697'}
        if not self._check_chain_has_rule(nat, c_name, rule):
            return False

        ips_qr = [item for sublist in map(lambda x: x['ip'], qr_intfs) for
                  item in sublist]
        ips_rfp = [item for sublist in map(lambda x: x['ip'], rfp_intfs) for
                   item in sublist]

        for intf in rfp_intfs:
            c_name = 'neutron-l3-agent-PREROUTING'
            for ip_m in intf['ip'][1:]:  # check each floating ip
                dip = ip_m.split('/')[0]  # real floating ip for destination
                if not ipInNetworks(dip, ips_rfp):
                    warn(r('dip %s not in rfp ports %s\n'
                           % (dip, ips_rfp)))
                    return False
                rule = nat.get_rule(c_name, {'destination': dip})
                sip = rule.get_flags().split(':')[1]
                if not ipInNetworks(sip, ips_qr):
                    warn(r('sip %s not in qr port %s\n' % (sip, ips_qr)))
                    return False
                rule_expect = {'in': '*', 'source': '*', 'out': '*',
                               'destination': dip, 'target': 'DNAT',
                               'prot': '*', 'flags': 'to:'+sip}
                if not rule.is_match(rule_expect):
                    warn(r('rule not matched in %s\n' % (c_name)))
                    return False
                if not self._check_chain_has_rule(nat,
                                                  'neutron-l3-agent-OUTPUT',
                                                  rule_expect):
                    return False
                else:
                    output(g('DNAT for incomping: %s --> %s passed\n'
                             % (dip, sip)))
                rule_expect = {'in': '*', 'source': sip, 'out': '*',
                               'destination': '*', 'target': 'SNAT',
                               'prot': '*', 'flags': 'to:'+dip}
                if not self._check_chain_has_rule(
                        nat,
                        'neutron-l3-agent-float-snat',
                        rule_expect):
                    return False
                else:
                    output(g('SNAT for outgoing: %s --> %s passed\n'
                             % (sip, dip)))
        return True

    def _compute_check_nat_table(self, ns_q, ns_fip):
        """
        Check the snat rules in the given ns
        :param ns_q:
        :param ns_fip:
        :return:
        """
        ipt = IPtables(ns_q)
        nat = ipt.get_table(table='nat')
        chains = [
            'neutron-postrouting-bottom',
            'neutron-l3-agent-OUTPUT',
            'POSTROUTING',
            'neutron-l3-agent-PREROUTING',
            'PREROUTING',
            'neutron-l3-agent-float-snat',
            'OUTPUT',
            'INPUT',
            'neutron-l3-agent-POSTROUTING',
            'neutron-l3-agent-snat',
        ]
        for c_name in chains:
            c = nat.get_chain(c_name)
            if not c:
                warn(r("Not found chain %s\n" % c_name))
                return False
            if c.get_policy() != 'ACCEPT':
                warn(r("Chain %s's policy is not ACCEPT\n" % c.name))

        for c_name in ['neutron-postrouting-bottom',
                       'OUTPUT', 'neutron-l3-agent-snat']:
            if not self._check_chain_rule_num(nat, c_name, 1):
                return False

        c_name = 'neutron-postrouting-bottom'
        rule = {'in': '*', 'source': '*', 'out': '*', 'destination': '*',
                'target': 'neutron-l3-agent-snat', 'prot': '*'}
        if not self._check_chain_has_rule(nat, c_name, rule):
            return False

        c_name = 'PREROUTING'
        rule = {'in': '*', 'source': '*', 'out': '*', 'destination': '*',
                'target': 'neutron-l3-agent-PREROUTING', 'prot': '*'}
        if not self._check_chain_has_rule(nat, c_name, rule):
            return False

        c_name = 'OUTPUT'
        rule = {'in': '*', 'source': '*', 'out': '*', 'destination': '*',
                'target': 'neutron-l3-agent-OUTPUT', 'prot': '*'}
        if not self._check_chain_has_rule(nat, c_name, rule):
            return False

        c_name = 'POSTROUTING'
        rule = {'in': '*', 'source': '*', 'out': '*', 'destination': '*',
                'target': 'neutron-l3-agent-POSTROUTING', 'prot': '*'}
        if not self._check_chain_has_rule(nat, c_name, rule):
            return False
        rule = {'in': '*', 'source': '*', 'out': '*', 'destination': '*',
                'target': 'neutron-postrouting-bottom', 'prot': '*'}
        if not self._check_chain_has_rule(nat, c_name, rule):
            return False

        c_name = 'neutron-l3-agent-POSTROUTING'
        rfp_intfs = NameSpace(ns_q).find_intfs('rfp-')
        for intf in rfp_intfs:
            rule = {'in': '!'+intf['intf'], 'source': '*',
                    'out': '!'+intf['intf'], 'destination': '*',
                    'target': 'ACCEPT', 'prot': '*',
                    'flags': '! ctstate DNAT'}
            if not self._check_chain_has_rule(nat, c_name, rule):
                return False

        qr_intfs = NameSpace(ns_q).find_intfs('qr-')
        if not self._compute_check_nat_rules(qr_intfs, rfp_intfs, nat,
                                                  ns_fip):
            return False

        return True


    def _compute_check_snat_ns(self, ns_router):
        """
        Check the local router namespace on compute node
        :param ns_router:
        :return: list of the fip ns
        """
        if not ns_router:
            return False
        intfs = NameSpace(ns_router).get_intfs()
        rfp_ports = []  # list of {'intf':eth0, 'ip':[]}
        for i in intfs:  # check each intf in this ns
            p = intfs[i]['intf']
            if p.startswith('rfp-'):  # rfp port in q connect to fpr in fip
                rfp_ports.append(p)
                output(b('### Checking rfp port %s\n' % p))
                if len(intfs[i]['ip']) < 2:
                    warn(r('Missing ips for port %s\n' % p))
                    continue
                else:
                    output(g('Found associated floating ips : %s\n'
                             % ', '.join(intfs[i]['ip'][1:])))
                ns_fip = self.nss.get_intf_by_name('fpr-'+intfs[i]['intf'][4:])
                if not ns_fip:
                    warn(r('Cannot find fip ns for %s\n' % q))
                    return False
                if not self._compute_check_fip_ns(intfs[i], ns_fip):
                    warn(r('Checking fip ns failed\n'))
                    return False
                if not self._compute_check_nat_table(ns_router, ns_fip):
                    warn(r('Checking qrouter ns nat table failed\n'))
                    return False
        if not rfp_ports:
            warn(r('Cannot find rfp port in ns %s\n' % ns_router))
            return False
        elif len(rfp_ports) > 1:
            warn(r('More than 1 rfp ports in ns %s\n' % ns_router))
            return False
        return True

    def _compute_check_fip_ns(self, rfp_port, ns_fip):
        """
        Check a fip namespace on compute node
        :param rfp_port:
        :return: True or False
        """
        q = 'fpr-'+rfp_port['intf'][4:]
        output(b('### Checking associated fpr port %s\n' % q))
        #self.nss.show(ns_fip)
        output(b('### Check related fip_ns=%s\n' % ns_fip))
        fpr_port = NameSpace(ns_fip).get_intf_by_name(q)
        if not fpr_port:
            warn(r('Cannot find fpr_port in fip ns %s\n' % ns_fip))
            return False
        a_ip, a_mask = rfp_port['ip'][0].split('/')
        b_ip, b_mask = fpr_port['ip'][0].split('/')
        if networkMask(a_ip, a_mask) != networkMask(b_ip, b_mask):
            warn(r('Different subnets for %s and %s\n'
                 % (rfp_port['ip'][0], fpr_port['ip'][0])))
            return False
        else:
            output(g('Bridging in the same subnet\n'))
        fg_port = NameSpace(ns_fip).find_intf('fg-')
        if not fg_port:
            warn('Cannot find fg_port in fip ns %s\n' % ns_fip)
            return False
        if fg_port['intf'] in Bridge('br-ex').get_ports():
            output(g('fg port is attached to br-ex\n'))
        else:
            warn(g('fg port is NOT attached to br-ex\n'))
            return False
        for float_ip in rfp_port['ip'][1:]:
            ip = float_ip.split('/')[0]
            if ipInNetwork(ip, fg_port['ip'][0]):
                output(g('floating ip %s match fg subnet\n' % ip))
            else:
                warn(r('floating ip %s No match the fg subnet' % ip))
                return False
        return True

    def _compute_check_vports(self):
        """
        Check the vport related information and rules
        :return:
        """
        checked_ns = []
        output(b('>>> Checking vports ...\n'))
        for port in self.br_int.get_ports():
            if port.startswith('qr-'):  # qrouter port
                output(b('## Checking router port = %s\n' % port))
                nsrouter = self.nss.get_intf_by_name(port)
                if nsrouter in checked_ns:
                    output(g('Checking passed already\n'))
                    continue
                else:
                    checked_ns.append(nsrouter)  # the names of the ns checked
                    if not self._compute_check_snat_ns(nsrouter):
                        warn(r('<<< Checking vports failed\n'))
                        return False
        output(b('<<< Checking vports passed\n'))
        return True

    def _compute_check_config_files(self):
        """
        Check related configuration files
        :return: True if no warning
        """
        warns = False
        output(b('>>> Checking config files...\n'))
        file = '/etc/sysctl.conf'
        lines = [
            'net.ipv4.ip_forward=1',
            'net.ipv4.conf.default.rp_filter=0',
            'net.ipv4.conf.all.rp_filter=0',
            'net.bridge.bridge-nf-call-iptables=1',
            'net.bridge.bridge-nf-call-ip6tables=1'
        ]
        output(b('# Checking file = %s...\n' % file))
        for l in lines:
            if not fileHasLine(file, l):
                warn(r('file %s NOT has %s\n' % (file, l)))
                warns = True

        file = '/etc/neutron/neutron.conf'
        lines = [
            '[DEFAULT]',
            #'router_distributed = True',
            'core_plugin = neutron.plugins.ml2.plugin.Ml2Plugin',
            'allow_overlapping_ips = True',
        ]
        output(b('# Checking file = %s...\n' % file))
        for l in lines:
            if not fileHasLine(file, l):
                warn(r('file %s NOT has %s\n' % (file, l)))
                warns = True

        file = '/etc/neutron/plugins/ml2/ml2_conf.ini'
        lines = [
            '[agent]',
            'l2_population = True',
            'enable_distributed_routing = True',
            'arp_responder = True',
        ]
        output(b('# Checking file = %s...\n' % file))
        for l in lines:
            if not fileHasLine(file, l):
                warn(r('file %s Not has %s\n' % (file, l)))
                warns = True

        file = '/etc/neutron/l3_agent.ini'
        lines = [
            '[DEFAULT]',
            'use_namespaces = True',
            'router_delete_namespaces = True',
            'agent_mode = dvr',
        ]
        output(b('# Checking file = %s...\n' % file))
        for l in lines:
            if not fileHasLine(file, l):
                warn(r('file %s NOT has %s\n' % (file, l)))
                warns = True
        if not warns:
            output(g('<<< Checking config files passed\n'))
            return True
        else:
            warn(r('<<< Checking config files has warnings\n'))
            return False

    def _compute_check_bridges(self):
        """
        Check the bridge information
        :return:
        """
        output(b('>>> Checking bridges...\n'))
        bridges = get_all_bridges()
        names = bridges.keys()
        brvlan = [e for e in names
                  if e not in ['br-int', 'br-ex', 'br-tun']]
        if not brvlan:
            warn(r('No vlan bridge is found\n'))
            return False
        brvlan = brvlan[0]
        output(b('# Existing bridges are %s\n' % ', '.join(names)))
        if 'br-int' not in names:
            warn(r('No integration bridge is found\n'))
            return False
        else:
            br = Bridge('br-int')
            if not br.has_port('int-'+brvlan):
                warn(r('port %s not found in br-int\n' % 'int-'+brvlan))
                return False
            if not br.has_port('patch-tun'):
                warn(r('port %s not found in br-int\n' % 'patch-tun'))
                return False

        if 'br-ex' not in names:
            warn(r('No external bridge is found\n'))
            return False

        if 'br-tun' not in names:
            warn(r('No tunnel bridge is found\n'))
            return False
        else:
            br = Bridge('br-tun')
            if not br.has_port('patch-int'):
                warn(r('port %s not found in br-tun\n' % 'patch-int'))
                return False

        br = Bridge(brvlan)
        if not br.has_port('phy-'+brvlan):
            warn(r('port %s not found in %s\n' % ('phy-'+brvlan, brvlan)))
            return False

        output(b('# Vlan bridge is at %s\n' % ', '.join(names)))
        output(g('<<< Checking bridges passed\n'))
        return True

    def _compute_node_check(self):
        """
        Check the qrouter-***  fip-*** spaces in the compute node.
        :return:
        """
        output(b('=== Checking DVR on compute node ===\n'))
        flag = True
        if not self._compute_check_config_files():
            flag = False
        output('\n')
        if not self._compute_check_bridges():
            flag = False
        output('\n')
        if not self._compute_check_vports():
            flag = False
        return flag

    def _check_network_node(self):
        """
        Check the qrouter-***  fip-*** snat-*** spaces in the network node.
        :return:
        """
        pass
