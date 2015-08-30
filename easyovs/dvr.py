__author__ = 'baohua'

from subprocess import call, Popen, PIPE
from easyovs.namespaces import NameSpace, NameSpaces
from easyovs.log import error, output, warn
from easyovs.util import r, g, b, ipStrToNum, networkMask, ipInNetwork, \
    ipInNetworks, fileHasLine, get_all_bridges, numToipStr
from easyovs.bridge import Bridge
from easyovs.iptables import IPtables


class DVR(object):
    """
    DVR configuration
    """
    def __init__(self):
        """
        """
        self.node = None
        self.br_int = Bridge('br-int')
        self.nss = NameSpaces()

    def check(self, _node=None):
        guess = 'compute'
        for ns_id in NameSpaces().get_ids():
            if ns_id.startswith('snat-'):  # only network has snat-*
                guess = 'network'
                break
        if not _node:
            output(b('# No node type given, guessing...%s node\n' % guess))
        else:  # given _node, will check if match
            if _node not in guess:
                warn(r('# Given node type=%s not match the server\n' % _node))
                guess = _node
        node = guess
        if node in 'compute':
            return self._compute_node_check()
        elif node in 'network':
            return self._network_node_check()
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
                    output(g('DNAT for incoming: %s --> %s passed\n'
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


    def _compute_check_router_ns(self, ns_router):
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
                q = 'fpr-'+intfs[i]['intf'][4:]
                ns_fip = self.nss.get_ns_by_port(q)
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
        if networkMask(rfp_port['ip'][0]) != networkMask(fpr_port['ip'][0]):
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
                nsrouter = self.nss.get_ns_by_port(port)
                if nsrouter in checked_ns:
                    output(g('Checking passed already\n'))
                    continue
                else:
                    checked_ns.append(nsrouter)  # the names of the ns checked
                    if not self._compute_check_router_ns(nsrouter):
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
        #  check br-int
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

        #  check br-ex
        if 'br-ex' not in names:
            warn(r('No external bridge is found\n'))
            return False
        else:
            br = Bridge('br-ex')
            if not br.has_port_start_with('fg-'):
                warn(r('No fg port found in br-ex\n'))

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

    def _compute_check_processes(self):
        """
        Check related configuration files
        :return: True if no warning
        """
        output(b('>>> Checking processes...\n'))
        warns = False
        cmd = "ps aux|grep neutron|grep python|grep -v grep"
        result, err = \
            Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True).communicate()
        if err:
            return False

        for p in [
            'neutron-metadata-agent',
            'neutron-openvswitch-agent',
            'neutron-l3-agent',
            #'neutron-ns-metadata-proxy',
            ]:
            if p not in result:
                warn(r('%s service is not running\n' % p))
                warns = True

        if not warns:
            output(g('<<< Checking processes passed\n'))
            return True
        else:
            warn(r('<<< Checking processes has warnings\n'))
            return False


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
        if flag:
            output(g('=== PASSED Checking DVR on compute node ===\n'))
        else:
            warn(r('=== FAILED Checking DVR on compute node ===\n'))
        return flag

    def _network_node_check(self):
        """
        Check the qrouter-***  fip-*** snat-*** spaces in the network node.
        :return:
        """
        output(b('=== Checking DVR on network node ===\n'))
        flag = True
        if not self._network_check_config_files():
            flag = False
        output('\n')
        if not self._network_check_processes():
            flag = False
        output('\n')
        if not self._network_check_bridges():
            flag = False
        output('\n')
        if not self._network_check_vports():
            flag = False
        if flag:
            output(g('=== PASSED Checking DVR on network node ===\n'))
        else:
            warn(r('=== FAILED Checking DVR on network node ===\n'))
        return flag

    def _network_check_config_files(self):
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
        ]
        output(b('# Checking file = %s...\n' % file))
        for l in lines:
            if not fileHasLine(file, l):
                warn(r('file %s NOT has %s\n' % (file, l)))
                warns = True

        file = '/etc/neutron/neutron.conf'
        lines = [
            '[DEFAULT]',
            'router_distributed = True',
            'core_plugin = neutron.plugins.ml2.plugin.Ml2Plugin',
            'allow_overlapping_ips = True',
            'allow_automatic_l3agent_failover = True',
        ]
        output(b('# Checking file = %s...\n' % file))
        for l in lines:
            if not fileHasLine(file, l):
                warn(r('file %s NOT has %s\n' % (file, l)))
                warns = True

        file = '/etc/neutron/plugins/ml2/ml2_conf.ini'
        lines = [
            '[securitygroup]',
            'enable_security_group = True',
            'enable_ipset = True',
            '[ovs]',
            'bridge_mappings = external:br-ex',
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
            #'external_network_bridge =',
            'router_delete_namespaces = True',
            'agent_mode = dvr_snat',
        ]
        output(b('# Checking file = %s...\n' % file))
        for l in lines:
            if not fileHasLine(file, l):
                warn(r('file %s NOT has %s\n' % (file, l)))
                warns = True

        file = '/etc/neutron/dhcp_agent.ini'
        lines = [
            '[DEFAULT]',
            'interface_driver = neutron.agent.linux.interface.OVSInterfaceDriver',
            'dhcp_driver = neutron.agent.linux.dhcp.Dnsmasq',
            'use_namespaces = True',
            'dhcp_delete_namespaces = True',
            'dnsmasq_config_file = /etc/neutron/dnsmasq-neutron.conf'
        ]
        output(b('# Checking file = %s...\n' % file))
        for l in lines:
            if not fileHasLine(file, l):
                warn(r('file %s Not has %s\n' % (file, l)))
                if l == lines[-1]:
                    warn(r(' Suggest change MTU if using VXLAN, '))
                    warn(r('adding following line into '
                           '/etc/neutron/dnsmasq-neutron.conf\n'))
                    warn(r(' dhcp-option-force=26,1450\n'))
                warns = True
        if not warns:
            output(g('<<< Checking config files passed\n'))
            return True
        else:
            warn(r('<<< Checking config files has warnings\n'))
            return False

    def _network_check_processes(self):
        """
        Check related configuration files
        :return: True if no warning
        """
        output(b('>>> Checking processes...\n'))
        warns = False
        cmd = "ps aux|grep neutron|grep python"
        result, err = \
            Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True).communicate()
        if err:
            return []

        for p in [
            'neutron-server',
            'neutron-dhcp-agent',
            'neutron-metadata-agent',
            'neutron-openvswitch-agent',
            'neutron-l3-agent',
            #'neutron-ns-metadata-proxy',
            ]:
            if p not in result:
                warn(r('%s service is not running\n' % p))
                warns = True

        if not warns:
            output(g('<<< Checking processes passed\n'))
            return True
        else:
            warn(r('<<< Checking processes has warnings\n'))
            return False

    def _network_check_bridges(self):
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
        # check br-int
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

        # check br-ex
        if 'br-ex' not in names:
            warn(r('No external bridge is found\n'))
            return False
        else:
            br = Bridge('br-ex')
            if not br.has_port_start_with('qg-'):
                warn(r('No qg port found in br-ex\n'))

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

    def _network_check_vports(self):
        """
        Check the vport related information and rules
        :return:
        """
        checked_ns = []
        output(b('>>> Checking vports ...\n'))
        qr_ports, dhcp_ports, sg_ports = [], [], []
        qr_ports_ips = []
        br_ports = self.br_int.get_ports()
        for port in br_ports:
            if port.startswith('qr-'):  # qrouter port
                qr_ports.append(port)
            elif port.startswith('tap'):  # qrouter port
                dhcp_ports.append(port)
            elif port.startswith('sg-'):  # qrouter port
                sg_ports.append(port)
        if not qr_ports:
            output('# no qrouter port found\n')
        if not dhcp_ports:
            output('# no dhcp port found\n')
        if not sg_ports:
            output('# no sg port found\n')
        for port in qr_ports:
            output(b('## Checking router port = %s\n' % port))
            ns_router = self.nss.get_ns_by_port(port)
            if ns_router in checked_ns:
                output(g('Checking passed already\n'))
            else:
                checked_ns.append(ns_router)  # the names of the ns checked
                if not self._network_check_router_ns(ns_router):
                    warn(r('<<< Checking vports failed\n'))
                    return False
            qr_ports_ips.extend(NameSpace(ns_router).get_ip_of_intf(
                port))
        for port in dhcp_ports:
            output(b('## Checking dhcp port = %s\n' % port))
            ns_dhcp = self.nss.get_ns_by_port(port)
            if ns_dhcp in checked_ns:
                output(g('Checking passed already\n'))
            else:
                checked_ns.append(ns_dhcp)  # the names of the ns checked
                if not self._network_check_dhcp_ns(ns_dhcp):
                    warn(r('<<< Checking vports failed\n'))
                    return False
        for port in sg_ports:  # snat port
            output(b('## Checking sg port = %s\n' % port))
            ns_snat = self.nss.get_ns_by_port(port)
            if ns_snat in checked_ns:
                output(g('Checking passed already\n'))
            else:
                checked_ns.append(ns_snat)  # the names of the ns checked
                if not self._network_check_snat_ns(ns_snat, qr_ports_ips):
                    warn(r('<<< Checking vports failed\n'))
                    return False
        output(g('<<< Checking vports passed\n'))
        return True

    def _network_check_router_ns(self, ns_router):
        """
        Check the local router namespace on compute node
        :param ns_router:
        :return: list of the fip ns
        """
        output(b('### Checking router ns = %s\n' % ns_router))
        if not ns_router:
            return False
        intfs = NameSpace(ns_router).get_intfs()
        r_ports = []  # list of {'intf':eth0, 'ip':[]}
        for i in intfs:  # check each intf in this ns
            p = intfs[i]['intf']
            if p == 'lo':  # ignore the lo port
                continue
            elif not p.startswith('qr-'):  # no router port?
                warn(r('Invalid port %s in %s\n' % (p, ns_router)))
                return False
            else:
                output(b('### Checking port %s\n' % p))
                r_ports.append(p)
                if not intfs[i]['ip']:
                    warn(r('No ip with port %s in %s\n' % (p, ns_router)))
                    return False
                else:
                    for ip_m in intfs[i]['ip']:
                        ip, mask = ip_m.split('/')
                        if ipStrToNum(ip) != networkMask(ip_m) + 1:
                            warn(r('IP %s is not gw on port %s\n' % (ip_m,
                                                                  ns_router)))
                            return False
        if not r_ports:
            warn(r('Cannot find router port in ns %s\n' % ns_router))
            return False
        return True

    def _network_check_dhcp_ns(self, ns_dhcp):
        """
        Check the local router namespace on compute node
        :param ns_router:
        :return: list of the fip ns
        """
        output(b('### Checking dhcp ns = %s\n' % ns_dhcp))
        if not ns_dhcp:
            return False
        warns = False
        intfs = NameSpace(ns_dhcp).get_intfs()
        dhcp_ports = []  # list of {'intf':eth0, 'ip':[]}
        for i in intfs:  # check each intf in this ns
            p = intfs[i]['intf']
            if p == 'lo':  # ignore the lo port
                continue
            elif not p.startswith('tap'):  # no router port?
                warn(r('Invalid port dhcp %s in %s\n' % (p, ns_dhcp)))
                return False
            else:
                output(b('### Checking dhcp port %s\n' % p))
                dhcp_ports.append(p)
                if not intfs[i]['ip']:
                    warn(r('No ip with dhcp port %s in %s\n' % (p, ns_dhcp)))
                    return False
                else:
                    for ip_m in intfs[i]['ip']:
                        if ip_m.startswith('169.254'):
                            continue
                        net_addr = numToipStr(networkMask(ip_m))
                        cmd = 'ps aux|grep dnsmasq|grep %s|grep -v grep'\
                              % net_addr
                        result, err = \
                            Popen(cmd, stdout=PIPE, stderr=PIPE,
                                  shell=True).communicate()
                        if err:
                            warn(r(err))
                            return False
                        if not result:
                            warn(r('Invalid dnsmasq process\n'))
                            return False
        if not dhcp_ports:
            warn(r('Cannot find dhcp port in ns %s\n' % ns_dhcp))
            return False
        return True

    def _network_check_snat_ns(self, ns_snat, qr_ports_ips):
        """
        Check the local router namespace on compute node
        :param ns_snat:
        :return: list of the fip ns
        """
        output(b('### Checking snat ns = %s\n' % ns_snat))
        if not ns_snat:
            return False
        intfs = NameSpace(ns_snat).get_intfs()
        sg_ports, qg_ports = [], []
        sg_ports_ips = []
        for i in intfs:  # check each intf in this ns
            p = intfs[i]['intf']
            if p == 'lo':  # ignore the lo port
                continue
            elif p.startswith('sg-'):  # no router port?
                sg_ports.append(p)
                sg_ports_ips.extend(intfs[i]['ip'])
            elif p.startswith('qg-'):  # no router port?
                qg_ports.append(p)

        if set(map(lambda x: networkMask(x), sg_ports_ips)) != \
                set(map(lambda x: networkMask(x), qr_ports_ips)):
            warn(r('qrouter ports not matched with sg ports\n'))
            return False

        if not sg_ports:
            warn(r('Cannot find sg port in ns %s\n' % ns_snat))
            return False
        if not qg_ports:
            warn(r('Cannot find qg port in ns %s\n' % ns_snat))
            return False
        if not self._network_check_nat_table(ns_snat):
            warn(r('Checking snat ns %s nat table failed\n' % ns_snat))
            return False
        return True

    def _network_check_nat_table(self, ns_snat):
        ipt = IPtables(ns_snat)
        nat = ipt.get_table(table='nat')
        qg_intfs = NameSpace(ns_snat).find_intfs('qg-')
        chains = [
            'PREROUTING',
            'INPUT',
            'OUTPUT',
            'POSTROUTING',
            'neutron-l3-agent-OUTPUT',
            'neutron-l3-agent-PREROUTING',
            'neutron-l3-agent-POSTROUTING',
            'neutron-l3-agent-float-snat',
            'neutron-l3-agent-snat',
            'neutron-postrouting-bottom',
        ]
        for c_name in chains:
            c = nat.get_chain(c_name)
            if not c:
                warn(r("Not found chain %s\n" % c_name))
                return False
            if c.get_policy() != 'ACCEPT':
                warn(r("Chain %s's policy is not ACCEPT\n" % c.name))

        for c_name in ['PREROUTING', 'neutron-postrouting-bottom',
                       'OUTPUT']:
            if not self._check_chain_rule_num(nat, c_name, 1):
                warn(r("Chain %s's size mismatch\n" % c_name))
                return False

        c_name = 'OUTPUT'
        rule = {'in': '*', 'source': '*', 'out': '*', 'destination': '*',
                'target': 'neutron-l3-agent-OUTPUT', 'prot': '*'}
        if not self._check_chain_has_rule(nat, c_name, rule):
            warn(r("Chain %s's rule failed\n" % c_name))
            return False

        c_name = 'POSTROUTING'
        rule = {'in': '*', 'source': '*', 'out': '*', 'destination': '*',
                'target': 'neutron-l3-agent-POSTROUTING', 'prot': '*'}
        if not self._check_chain_has_rule(nat, c_name, rule):
            warn(r("Chain %s's rule failed\n" % c_name))
            return False
        rule = {'in': '*', 'source': '*', 'out': '*', 'destination': '*',
                'target': 'neutron-postrouting-bottom', 'prot': '*'}
        if not self._check_chain_has_rule(nat, c_name, rule):
            warn(r("Chain %s's rule failed\n" % c_name))
            return False

        c_name = 'neutron-l3-agent-POSTROUTING'
        for intf in qg_intfs:
            rule = {'in': '!'+intf['intf'], 'source': '*',
                    'out': '!'+intf['intf'], 'destination': '*',
                    'target': 'ACCEPT', 'prot': '*',
                    'flags': '! ctstate DNAT'}
            if not self._check_chain_has_rule(nat, c_name, rule):
                warn(r("Chain %s's rule failed\n" % c_name))
                return False

        c_name = 'neutron-l3-agent-snat'
        for intf in qg_intfs:
            for ip_m in intf['ip']:
                ip = ip_m.split('/')[0]
                rule = {'in': '*', 'source': '*', 'out': intf['intf'],
                        'destination': '*', 'target': 'SNAT', 'prot': '*',
                        'flags': 'to:'+ip}
                if not self._check_chain_has_rule(nat, c_name, rule):
                    warn(r("Chain %s's rule failed\n" % c_name))
                    return False
                rule = {'in': '*', 'source': '*', 'out': '*',
                        'destination': '*', 'target': 'SNAT', 'prot': '*'}
                if not self._check_chain_has_rule(nat, c_name, rule):
                    warn(r("Chain %s's rule failed\n" % c_name))
                    return False

        c_name = 'neutron-postrouting-bottom'
        rule = {'in': '*', 'source': '*', 'out': '*', 'destination': '*',
                'target': 'neutron-l3-agent-snat', 'prot': '*'}
        if not self._check_chain_has_rule(nat, c_name, rule):
            warn(r("Chain %s's rule failed\n" % c_name))
            return False

        return True
