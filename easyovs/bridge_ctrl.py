__author__ = 'baohua'

from subprocess import Popen, PIPE

from easyovs.bridge import Bridge
from easyovs.flow import Flow
from easyovs.log import debug, error, output
from easyovs.neutron import neutron_handler
from easyovs.util import color_str, get_all_bridges


def br_addflow(bridge, flow):
    if 'actions=' in flow and len(flow.split()) == 2:
        return Bridge(bridge).add_flow(flow)
    else:
        return False


def br_delflow(bridge, ids, forced=False):
    debug('br_delflow: %s: %s\n' % (bridge, ','.join(ids)))
    if type(ids) == str and ids.isdigit():
        return Bridge(bridge).del_flow([ids], forced)
    else:
        return Bridge(bridge).del_flow(ids, forced)

def br_exists(name):
    """
    Return True of False of a bridge's existence.
    """
    if isinstance(name, str):
        return Bridge(name).exists()
    else:
        return False


def br_list():
    """
    List available bridges.
    """
    bridges = get_all_bridges()
    if not bridges:
        output('None bridge exists. Might try using root privilege?\n')
        return
    br_info = ''
    for br in sorted(bridges.keys()):
        br_info += color_str("%s\n" % br, 'r')
        if bridges[br]['Port']:
            br_info += "\tPort:\t\t%s\n" \
                       % (' '.join(sorted(bridges[br]['Port'].keys())))
        if bridges[br]['Controller']:
            br_info += "\tController:\t%s\n" \
                       % (' '.join(bridges[br]['Controller']))
        if bridges[br]['fail_mode']:
            br_info += "\tFail_Mode:\t%s\n" % (bridges[br]['fail_mode'])
    output(br_info)

def br_addbr(name):
    """
    Create a new bridge.
    """
    cmd = "ovs-vsctl --may-exist add-br %s" % name
    result, err = \
        Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True).communicate()
    if err:
        error("Error when adding new bridge %s\n" % name)
    else:
        output("bridge %s was created\n" % name)

def br_delbr(name):
    """
    Delete a bridge.
    """
    cmd = "ovs-vsctl --if-exists del-br %s" % name
    result, err = \
        Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True).communicate()
    if err:
        error("Error when deleting bridge %s\n" % name)
    else:
        output("bridge %s was deleted\n" % name)

def br_dump(name):
    """
    Dump the port information of a given bridges.
    """
    Bridge(name).dump_flows()

def br_show(name):
    """
    Show information of a given bridges.
    """
    ovs_ports = Bridge(name).get_ports()
    if not ovs_ports:
        return
    neutron_ports = neutron_handler.get_neutron_ports()
    debug('get neutron_ports\n')
    content = []
    mac_ip_show = False
    for intf in ovs_ports:  # e.g., qvo-xxx, int-br-eth0, qr-xxx, tapxxx
        port, tag, intf_type = \
            ovs_ports[intf]['port'], ovs_ports[intf]['vlan'], ovs_ports[
                intf]['type']
        if neutron_ports and intf[3:] in neutron_ports:
            p = neutron_ports[intf[3:]]
            vm_ips = ','.join(map(lambda x: x.get('ip_address'),
                                  p['fixed_ips']))
            vm_mac = p.get('mac_address')
            mac_ip_show = True
        else:
            vm_ips, vm_mac = '', ''
        content.append((intf, port, tag, intf_type, vm_ips, vm_mac))
        # output('%-20s%-8s%-16s%-24s%-8s\n' %(intf,port,vmIP,vmMac,tag))
    content.sort(key=lambda x: x[1])  # sort by port
    content.sort(key=lambda x: x[4])  # sort by vm_ip
    content.sort(key=lambda x: x[3])  # sort by type
    output(color_str('%-20s%-12s%-8s%-12s'
                     % ('Intf', 'Port', 'Vlan', 'Type'), 'r'))
    if mac_ip_show:
        output(color_str('%-16s%-24s\n' % ('vmIP', 'vmMAC'), 'r'))
    else:
        output('\n')
    i = 0
    for _ in content:
        #color = ['w','g'][i%2]
        color = 'b'
        output(color_str('%-20s%-12s%-8s%-12s'
                         % (_[0], _[1], _[2], _[3]), color))
        if mac_ip_show:
            output(color_str('%-16s%-24s\n' % (_[4], _[5]), color))
        else:
            output('\n')
        i += 1


def find_br_ports(port_id):
    '''
    Find a port with given id
    :param port_id: a4111776-bd

    :return: qr-a4111776-bd
    '''
    brs = get_all_bridges()
    for br_id in brs:
        if 'Port'in brs[br_id]:
            for p in brs[br_id]['Port']:
                if p.endswith(port_id):
                    return p
    return None
