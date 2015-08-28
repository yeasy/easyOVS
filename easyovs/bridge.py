__author__ = 'baohua'

from subprocess import call, Popen, PIPE
import re
import sys
import termios

from easyovs.util import get_all_bridges
from easyovs.flow import Flow
from easyovs.log import output, error, debug
from easyovs.util import get_num_after, get_str_before, get_str_between


def check_exist(func):
    def wrapper(self, *arg):
        if not self.exists():
            output(
                'The bridge does not exist.\n \
                Please check available bridges using list\n')
            return None
        else:
            return func(self, *arg)
    return wrapper


class Bridge(object):
    """
    An OpenvSwitch bridge, typically is a datapath, e.g., br-int
    """

    def __init__(self, name):
        self.bridge = name
        self.flows = []
        self.flows_db = '/tmp/tmp_%s.flows' % self.bridge

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
        err = Popen(addflow_cmd, stdout=PIPE, stderr=PIPE,
                    shell=True).communicate()[1]
        if err:
            output(err)
            error("Error when adding new flow <%s> to bridge %s\n"
                  % (flow, self.bridge))
            return False
        else:
            return True

    @check_exist
    def del_flow(self, flow_ids, forced=False):
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
                if forced:
                    del_flows.append(del_flow)
                else:
                    Flow.banner_output()
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
        f = open(self.flows_db, 'r')
        while True:
            lines = f.readlines(1000)
            if not lines:
                break
            for line in lines:
                flow = self._parse_flow(line)
                if flow in del_flows:
                    del_matches = line.replace(',', ' ').split()
                    del_matches = \
                        filter(lambda m: not (m.startswith("cookie=")
                               or m.startswith("actions=")), del_matches)
                    del_cmd = "ovs-ofctl --strict del-flows %s %s" \
                              % (self.bridge, ','.join(del_matches))
                    err = Popen(del_cmd, stdout=PIPE, stderr=PIPE,
                                shell=True).communicate()[1]
                    if err:
                        error("Error when delflow <%s> in bridge %s\n"
                              % (','.join(del_matches), self.bridge))
                        error(err)
                        return False
        f.close()
        self.load_flows()
        return True

    @check_exist
    def load_flows(self, db=False):
        """
        Load the OpenvSwitch table rules into self.flows, and to db if enabled.
        self.flows will be a list of Flow objects
        """
        debug('load_flows():\n')
        cmd = "ovs-ofctl dump-flows %s" % self.bridge
        flows, f = [], None
        if db:
            f = open(self.flows_db, 'w')
        result, err = \
            Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True).communicate()
        if err:
            return
        for l in result.split('\n'):
            l = l.strip()
            if l.startswith('cookie='):
                debug('%s\n' % l)
                flow = self._parse_flow(l)
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
        Return a dict of flows in the bridge in order of table:priority.
        """
        debug('Bridge:get_flow()\n')
        self.load_flows()
        if len(self.flows) > 0:
            return self.flows
        else:
            return {}

    def _parse_flow(self, line):
        """
        Return a Flow or None, converted from a given line of original flow.
        """
        line = line.strip()
        table, packet, priority, match, actions = 0, 0, 0, '', ''
        if line.startswith('cookie='):
            table = get_num_after(line, 'table=')
            packet = get_num_after(line, 'n_packets=')
            if table is None or packet is None:
                return None
            for field in line.split():
                if field.startswith('priority='):  # match starts with pri
                    priority = get_num_after(field, 'priority=')
                    if priority is None:
                        error('No priority field found in flow\n')
                        return None
                    match = \
                        field.replace('priority=%u'
                                      % priority, '').lstrip(',').strip()
                    if not match:
                        match = r'*'
                    port_no = get_num_after(field, 'in_port=')
                    if isinstance(port_no, int):
                        intf = self._get_port_intf(port_no)
                        if intf:
                            match = \
                                match.replace('in_port=%u'
                                              % port_no, 'in_port=%s' % intf)
                elif field.startswith('actions='):
                    actions = self._process_actions(field)
            if priority is None:  # There is no priority= field
                match = line.split()[len(line.split()) - 2]
            if len(match) >= 30:
                match.replace('vlan_tci', 'vlan')
                match = re.compile('0x0{1,}').sub('0x', match)
            return Flow(self.bridge, table, packet, priority, match, actions)
        else:
            return None

    def dump_flows(self):
        """
        Dump out the flows of this bridge
        :return:
        """
        self.load_flows()
        debug('br_dump: len flows=%u\n' % len(self.flows))
        table = 0
        if self.flows:
            Flow.banner_output()
            for f in self.flows:
                if f.table != table:
                    output('\n')
                    table = f.table
                f.fmt_output()


    def _process_actions(self, actions_str):
        """
        Process the actions fields to make it more readable
        :param actions_str: input action string
        :return: The converted string.
        """
        actions = actions_str.replace('actions=', '').rstrip('\n')
        for act in actions_str.split(','):
            if act.startswith('output:'):
                port_no = get_num_after(act, 'output:')
                if isinstance(port_no, int):
                    intf = self._get_port_intf(port_no)
                    if intf:
                        actions = \
                            actions.replace('output:%u'
                                            % port_no, 'output:%s' % intf)
        return actions

    def _get_port_intf(self, port_no):
        """
        Get the interface name for the ovs port id in the bridge.
        :param port_no: int number of ovs port
        :return: the interface name or None
        """
        if not port_no:
            return None
        ovs_ports = self.get_ports()
        for intf in ovs_ports:
            if ovs_ports[intf].get('port') == str(port_no):
                return intf
        return None

    @check_exist
    def has_port(self, name):
        return name in self.get_ports()

    @check_exist
    def get_ports(self):
        """
        Return a dict of the ports (port, addr, tag, type) on the bridge, like
        {
            'qvoxxx':{
                'port':'2',
                'addr':'08:91:ff:ff:f3',
                'vlan':'1',
                'type':'internal',
            }
        }
        """
        ports = {}
        cmd = "ovs-ofctl show %s" % self.bridge
        result, error = \
            Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True).communicate()
        if error:
            return {}
        #output('%-8s%-16s%-16s\n' %('PORT','INTF','ADDR'))
        brs = get_all_bridges()
        for l in result.split('\n'):
            if l.startswith(' ') and l.find('(') >= 0 and l.find(')') >= 0:
                l = l.strip()
                port = get_str_before(l, '(')
                intf = get_str_between(l, '(', ')')
                addr = l[l.find('addr:') + len('addr:'):]
                #output('%-8s%-16s%-16s\n' %(port,intf,addr))
                if self.bridge in brs and intf in brs[self.bridge]['Port']:
                    tag = brs[self.bridge]['Port'][intf].get('vlan', '')
                    intf_type = brs[self.bridge]['Port'][intf].get('type', '')
                else:
                    tag, intf_type = '', ''
                ports[intf] = {'port': port, 'addr': addr, 'vlan': tag,
                               'type': intf_type}
        return ports
