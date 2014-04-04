__author__ = 'baohua'

from subprocess import call, Popen, PIPE
import sys
import termios

from easyovs.log import output, debug
from easyovs.util import get_numstr_after, get_str_before, get_str_between
from flow import Flow
from neutron import get_neutron_ports


def check_exist(func):
    def wrapper(self, *arg):
        if not self.exists():
            output('The bridge does not exist.\n You can check available bridges using list\n')
            return None
        else:
            return func(self, *arg)
    return wrapper


class Bridge(object):
    """
    An OpenvSwitch bridge, typically is a datapath, e.g., br-int
    """

    def __init__(self, bridge):
        self.bridge = bridge
        self.flows = []
        self.flows_db = '/tmp/tmp_%s_flows' % self.bridge

    def exists(self):
        if not self.bridge:
            return False
        cmd = "ovs-vsctl show|grep -q %s" % self.bridge
        return call(cmd, shell=True) == 0

    @check_exist
    def add_flow(self, flow):
        """
        Return True or False to add a flow.
        """
        if not flow:
            return False
        addflow_cmd = 'ovs-ofctl add-flow %s "%s"' % (self.bridge, flow)
        error = Popen(addflow_cmd, stdout=PIPE, stderr=PIPE, shell=True).communicate()[1]
        if error:
            output(error)
            return False
        else:
            return True

    @check_exist
    def del_flow(self, flow_ids):
        """
        Return True or False to del a flow from given list.
        """
        if len(flow_ids) <= 0:
            return False
        if not self.flows:
            self.load_flows()
        del_flows = []
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        for flow_id in flow_ids:
            if isinstance(flow_id, str) and flow_id.isdigit():
                flow_id = int(flow_id)
            else:
                continue
            if flow_id >= len(self.flows):
                continue
            else:
                del_flow = self.flows[flow_id]
                del_flow.fmt_output()
                output('Del the flow? [Y/n]: ')
                new = termios.tcgetattr(fd)
                new[3] = new[3] & ~termios.ICANON
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, new)
                    while True:
                        in_ch = sys.stdin.read(1)
                        if in_ch == 'n' or in_ch == 'N':
                            output('\tCancel the deletion.\n')
                            break
                        elif in_ch == 'y' or in_ch == 'Y' or in_ch != '\n':
                            del_flows.append(del_flow)
                            output('\n')
                            break
                        else:
                            output('\nWrong, please input [Y/n]: ')
                            continue
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)
        if not del_flows:
            return False
        self.load_flows(True)
        flows_db_new = self.flows_db + '.new'
        f, f_new = open(self.flows_db, 'r'), open(flows_db_new, 'w')
        while True:
            lines = f.readlines(1000)
            if not lines:
                break
            for line in lines:
                flow = self.parse_flow(line)
                if flow not in del_flows:
                    f_new.write('%s' % line)
                else:
                    debug("Del the flow:\n")
                    #del_flow.fmt_output()
        f.close()
        f_new.close()
        replace_cmd = "ovs-ofctl replace-flows %s %s" % (self.bridge, flows_db_new)
        error = Popen(replace_cmd, stdout=PIPE, stderr=PIPE, shell=True).communicate()[1]
        if error:
            output(error)
            return False
        else:
            self.load_flows()
            return True

    @check_exist
    def load_flows(self, db=False):
        """
        Load the OpenvSwitch table rules into self.flows, and also to db if enabled.
        """
        debug('load_flows:\n')
        cmd = "ovs-ofctl dump-flows %s" % self.bridge
        flow_id, flows, f = 0, [], None
        if db:
            f = open(self.flows_db, 'w')
        result, error = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True).communicate()
        if error:
            return
        for l in result.split('\n'):
            l = l.strip()
            if l.startswith('cookie='):
                flow = self.parse_flow(l)
                if flow:
                    flows.append(flow)
                    if db:
                        f.write('%s\n' % l)
        if db:
            f.close()
        flows.sort(reverse=True)
        for i in range(len(flows)):
            flows[i].id = i
        self.flows = flows
        debug('load_flows:len flows=%u\n' % len(self.flows))

    @check_exist
    def get_flows(self):
        """
        Return a dict of flows in the bridge.
        """
        debug('Bridge:get_flow()\n')
        self.load_flows()
        if len(self.flows) > 0:
            return self.flows
        else:
            return {}

    def parse_flow(self, line):
        """
        Return a Flow or None, converted from a given line of original flow.
        """
        line = line.strip()
        table, packet, priority, match, actions = '', '', '', '', ''
        if line.startswith('cookie='):
            table = get_numstr_after(line, 'table=')
            packet = get_numstr_after(line, 'n_packets=')
            if not table or not packet:
                return None
            for field in line.split():
                if field.startswith('priority='):
                    priority = get_numstr_after(field, 'priority=')
                    if not priority:
                        return None
                    match = field.replace('priority=%s' % priority, '').lstrip(',').strip()
                    if not match:
                        match = r'*'
                elif field.startswith('actions='):
                    actions = field.replace('actions=', '').rstrip('\n')
            if priority is '':  # There is no priority= field
                match = line.split()[len(line.split()) - 2]
            return Flow(self.bridge, table, packet, priority, match, actions)
        else:
            return None

    @check_exist
    def get_ports(self):
        """
        Return a dict of the ports (port, addr, tag, type) on the bridge, looks like
        {
            'qvoxxx':{
                'port':2,
                'addr':08:91:ff:ff:f3,
                'vlan':1,
                'type':internal,
            }
        }
        """
        ports = {}
        cmd = "ovs-ofctl show %s" % self.bridge
        result, error = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True).communicate()
        if error:
            return {}
        #output('%-8s%-16s%-16s\n' %('PORT','INTF','ADDR'))
        bridges = get_bridges()
        for l in result.split('\n'):
            if l.startswith(' ') and l.find('(') >= 0 and l.find(')') >= 0:
                l = l.strip()
                port = get_str_before(l, '(')
                intf = get_str_between(l, '(', ')')
                addr = l[l.find('addr:') + len('addr:'):]
                #output('%-8s%-16s%-16s\n' %(port,intf,addr))
                if self.bridge in bridges and intf in bridges[self.bridge]['Port']:
                    tag = bridges[self.bridge]['Port'][intf].get('vlan', '')
                    intf_type = bridges[self.bridge]['Port'][intf].get('type', '')
                else:
                    tag, intf_type = '', ''
                ports[intf] = {'port': port, 'addr': addr, 'vlan': tag, 'type': intf_type}
        return ports


def br_addflow(bridge, flow):
    if 'actions=' in flow and len(flow.split()) == 2:
        return Bridge(bridge).add_flow(flow)
    else:
        return False


def br_delflow(bridge, ids):
    debug('br_delflow: %s: %s\n' % (bridge, ','.join(ids)))
    if type(ids) == str and ids.isdigit():
        return Bridge(bridge).del_flow([ids])
    else:
        return Bridge(bridge).del_flow(ids)


def br_getflows(bridge):
    if isinstance(bridge, str):
        return Bridge(bridge).get_flows()
    else:
        return None


def br_exists(bridge):
    """
    Return True of False of a bridge's existence.
    """
    if isinstance(bridge, str):
        return Bridge(bridge).exists()
    else:
        return False


def br_getports(bridge):
    """
    Return a dict of all available bridges.
    """
    if isinstance(bridge, str):
        return Bridge(bridge).get_ports()
    else:
        return {}


def br_list():
    """
    List available bridges.
    """
    bridges = get_bridges()
    if not bridges:
        output('None bridge exists.\n')
        return
    br_info = ''
    for br in sorted(bridges.keys()):
        br_info += "%s\n" % br
        if bridges[br]['Port']:
            br_info += " Port:\t\t%s\n" % (' '.join(bridges[br]['Port'].keys()))
        if bridges[br]['Controller']:
            br_info += " Controller:\t%s\n" % (' '.join(bridges[br]['Controller']))
        if bridges[br]['fail_mode']:
            br_info += " Fail_Mode:\t%s\n" % (bridges[br]['fail_mode'])
    output(br_info)


def br_dump(bridge):
    """
    Dump the port information of a given bridges.
    """
    flows = br_getflows(bridge)
    debug('br_dump: len flows=%u\n' % len(flows))
    if flows:
        Flow.banner_output()
        for f in flows:
            f.fmt_output()


def br_show(bridge):
    """
    Show information of a given bridges.
    """
    ovs_ports = br_getports(bridge)
    if not ovs_ports:
        return
    neutron_ports = get_neutron_ports()
    content = []
    mac_ip_show = False
    for intf in ovs_ports: # e.g., qvo-xxx, int-br-eth0, qr-xxx, tapxxx
        port, tag, intf_type = ovs_ports[intf]['port'], ovs_ports[intf]['vlan'], ovs_ports[intf]['type']
        if neutron_ports and intf[3:] in neutron_ports:
            vm_ip, vm_mac = neutron_ports[intf[3:]]['ip_address'], neutron_ports[intf[3:]]['mac']
            mac_ip_show = True
        else:
            vm_ip, vm_mac = '', ''
        content.append((intf, port, tag, intf_type, vm_ip, vm_mac))
        #output('%-20s%-8s%-16s%-24s%-8s\n' %(intf,port,vmIP,vmMac,tag))
    content.sort(key=lambda x: x[0])
    content.sort(key=lambda x: x[3])
    output('%-20s%-12s%-8s%-12s' % ('Intf', 'Port', 'Vlan', 'Type'))
    if mac_ip_show:
        output('%-16s%-24s\n' % ('vmIP', 'vmMAC'))
    else:
        output('\n')
    for _ in content:
        output('%-20s%-12s%-8s%-12s' % (_[0], _[1], _[2], _[3]))
        if mac_ip_show:
            output('%-16s%-24s\n' % (_[4], _[5]))
        else:
            output('\n')


def get_bridges():
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
                }
        },
    }
    """
    bridges, br = {}, ''
    cmd = 'ovs-vsctl show'
    result, error = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True).communicate()
    if error:
        return {}
    for l in result.split('\n'):
        l = l.strip().replace('"', '')
        if l.startswith('Bridge '):
            br = l.lstrip('Bridge ')
            bridges[br] = {}
            bridges[br]['Controller'] = []
            bridges[br]['Port'] = {}
            bridges[br]['fail_mode'] = ''
        else:
            if l.startswith('Controller '):
                bridges[br]['Controller'].append(l.replace('Controller ', ''))
            elif l.startswith('fail_mode: '):
                bridges[br]['fail_mode'] = l.replace('fail_mode: ', '')
            elif l.startswith('Port '):
                phy_port = l.replace('Port ', '')  # e.g., br-eth0
                bridges[br]['Port'][phy_port] = {'vlan': '', 'type': ''}
            elif l.startswith('tag: '):
                bridges[br]['Port'][phy_port]['vlan'] = l.replace('tag: ', '')
            elif l.startswith('Interface '):
                bridges[br]['Port'][phy_port]['intf'] = l.replace('Interface ', '')
            elif l.startswith('type: '):
                bridges[br]['Port'][phy_port]['type'] = l.replace('type: ', '')
    return bridges
