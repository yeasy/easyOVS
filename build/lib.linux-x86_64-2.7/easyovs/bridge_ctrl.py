__author__ = 'baohua'

from subprocess import call, Popen, PIPE

from easyovs.bridge import Bridge
from easyovs.flow import Flow
from easyovs.log import debug, error, output
from easyovs.neutron import neutron_handler
from easyovs.util import get_bridges, color_str


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
        output('None bridge exists. Might try using root privilege?\n')
        return
    br_info = ''
    for br in sorted(bridges.keys()):
        br_info += "%s\n" % br
        if bridges[br]['Port']:
            br_info += " Port:\t\t%s\n" \
                       % (' '.join(sorted(bridges[br]['Port'].keys())))
        if bridges[br]['Controller']:
            br_info += " Controller:\t%s\n" \
                       % (' '.join(bridges[br]['Controller']))
        if bridges[br]['fail_mode']:
            br_info += " Fail_Mode:\t%s\n" % (bridges[br]['fail_mode'])
    output(br_info)

def br_addbr(bridge):
    """
    Create a new bridge.
    """
    cmd = "ovs-vsctl --may-exist add-br %s" % bridge
    result, err = \
        Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True).communicate()
    if err:
        error("Error when adding new bridge %s\n" % bridge)
    else:
        output("bridge %s was created\n" % bridge)

def br_delbr(bridge):
    """
    Delete a bridge.
    """
    cmd = "ovs-vsctl --if-exists del-br %s" % bridge
    result, err = \
        Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True).communicate()
    if err:
        error("Error when deleting bridge %s\n" % bridge)
    else:
        output("bridge %s was deleted\n" % bridge)

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
    neutron_ports = neutron_handler.get_neutron_ports()
    debug('get neutron_ports', neutron_ports)
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
    output(color_str('r', '%-20s%-12s%-8s%-12s'
                     % ('Intf', 'Port', 'Vlan', 'Type')))
    if mac_ip_show:
        output(color_str('r', '%-16s%-24s\n' % ('vmIP', 'vmMAC')))
    else:
        output('\n')
    i = 0
    for _ in content:
        #color = ['w','g'][i%2]
        color = 'b'
        output(color_str(color, '%-20s%-12s%-8s%-12s'
                         % (_[0], _[1], _[2], _[3])))
        if mac_ip_show:
            output(color_str(color, '%-16s%-24s\n' % (_[4], _[5])))
        else:
            output('\n')
        i += 1
