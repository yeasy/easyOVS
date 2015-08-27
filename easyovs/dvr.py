__author__ = 'baohua'

from easyovs.bridge import Bridge
from easyovs.namespaces import NameSpace, NameSpaces
from easyovs.log import error, output, warn
from easyovs.util import color_str, dottedQuadToNum, networkMask, \
    ipInNetwork


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
        if node == 'compute':
            self._check_compute_node()
        elif node == 'network':
            self._check_network_node()
        else:
            error('Unknown node type=%s, compute or network?\n' % node)

    def _check_compute_node_local_ns(self, name):
        """
        Check the local router namespace on compute node
        :param name:
        :return: list of the fip ns
        """
        ns_router = name
        if not ns_router:
            return
        self.nss.show(ns_router)
        intfs = NameSpace(ns_router).get_intfs()
        rfp_ports = []  # list of {'intf':eth0, 'ip':[]}
        for i in intfs:  # check each intf in this ns
            if intfs[i]['intf'].startswith('rfp-'):
                self._check_compute_node_fip_ns(intfs[i])

    def _check_compute_node_fip_ns(self, rfp_port):
        """
        Check a fip namespace on compute node
        :param rfp_port:
        :return:
        """
        p = rfp_port['intf']  # check one rfp_port
        q = 'fpr-'+p[4:]
        ns_fip = self.nss.find_intf(q)
        if not ns_fip:
            warn('Cannot find fip ns for %s\n' % q)
            return
        self.nss.show(ns_fip)
        output('### Check related fip_ns=%s\n' % ns_fip)
        fpr_port = NameSpace(ns_fip).get_intf_by_name(q)
        if not fpr_port:
            warn('Cannot find fpr_port in fip ns %s\n' % ns_fip)
            return
        if len(rfp_port['ip']) < 2:
            warn(color_str('Missing ips for port %s\n' % rfp_port['intf'],
                           'r'))
            return
        else:
            output(color_str('Floating ips associated: %s\n'
                   % ', '.join(rfp_port['ip'][1:]),'g'))

        a_ip, a_mask = rfp_port['ip'][0].split('/')
        b_ip, b_mask = fpr_port['ip'][0].split('/')
        if networkMask(a_ip, a_mask) != networkMask(b_ip, b_mask):
            warn(color_str('Different subnets for %s and %s\n'
                 % (rfp_port['ip'][0], fpr_port['ip'][0]),'r'))
            return
        else:
            output(color_str('Bridging in the same subnet','g'))
        fg_port = NameSpace(ns_fip).find_intf('fg-')
        if not fg_port:
            warn('Cannot find fg_port in fip ns %s\n' % ns_fip)
            return
        for float_ip in rfp_port['ip'][1:]:
            ip = float_ip.split('/')[0]
            if ipInNetwork(ip, fg_port['ip'][0]):
                output(color_str('floating ip match fg subnet\n','g'))
            else:
                warn(color_str('floating ip No match the fg subnet','r'))

    def _check_compute_node(self):
        checked_ns = []
        for port in self.br_int.get_ports():
            if port.startswith('qr-'):  # qrouter port
                output(color_str('## Checking router port = %s\n' % port,
                                 'b'))
                ns_router = self.nss.find_intf(port)
                if ns_router in checked_ns:
                    output('Checked already\n')
                    continue
                else:
                    checked_ns.append(ns_router)  # the names of the ns checked
                    self._check_compute_node_local_ns(ns_router)
                pass
        pass

    def _check_network_node(self):
        pass
