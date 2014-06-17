__author__ = 'baohua'

from subprocess import Popen, PIPE

from easyovs.bridge import Bridge
from easyovs.flow import Flow
from easyovs.log import debug, output
from easyovs.neutron import get_neutron_ports
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
        output('None bridge exists.\n')
        return
    br_info = ''
    for br in sorted(bridges.keys()):
        br_info += "%s\n" % br
        if bridges[br]['Port']:
            br_info += " Port:\t\t%s\n" % (' '.join(sorted(bridges[br]['Port'].keys())))
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
    content.sort(key=lambda x: x[1]) #sort by port
    content.sort(key=lambda x: x[4]) #sort by vm_ip
    content.sort(key=lambda x: x[3]) #sort by type
    output(color_str('b','%-20s%-12s%-8s%-12s' % ('Intf', 'Port', 'Vlan', 'Type')))
    if mac_ip_show:
        output(color_str('b', '%-16s%-24s\n' % ('vmIP', 'vmMAC')))
    else:
        output('\n')
    i = 0
    for _ in content:
        color = ['w','g'][i%2]
        output(color_str(color, '%-20s%-12s%-8s%-12s' % (_[0], _[1], _[2], _[3])))
        if mac_ip_show:
            output(color_str(color, '%-16s%-24s\n' % (_[4], _[5])))
        else:
            output('\n')
        i += 1