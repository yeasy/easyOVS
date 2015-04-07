__author__ = 'baohua'

from oslo_config import cfg

import keystoneclient.v2_0.client as ksclient
from keystoneclient.openstack.common.apiclient.exceptions import \
    AuthorizationFailure, Unauthorized
import neutronclient.v2_0.client as neutronclient
import sys

from os.path import exists, getmtime
from time import time
import cPickle

from easyovs import config
from easyovs.log import output, warn
from easyovs.util import color_str

class NeutronHandler(object):
    """
    Handle neutron related information query.
    """
    def __init__(self):
        config.init(sys.argv[1:])
        try:
            self.keystone = ksclient.Client(auth_url=cfg.CONF.OS.auth_url,
                                   tenant_name=cfg.CONF.OS.tenant_name,
                                   username=cfg.CONF.OS.username,
                                   password=cfg.CONF.OS.password)
            self.token = self.keystone.auth_token
            neutron_endpoint_url = self.keystone.service_catalog.url_for(
                service_type='network')
            self.neutron = neutronclient.Client(endpoint_url=neutron_endpoint_url,
                                            token=self.token)
        except AuthorizationFailure:
            warn("OpenStack Authorization Failed\n")
            self.neutron = None
        except Unauthorized:
            warn("No valid OpenStack authentication information is found\n")
            self.neutron = None

    def get_neutron_ports(self, fresh=False):
        """
        Return the neutron port information, each line looks like
        '583c7038-d3':{'id':id,'name':name,'mac':mac,"subnet_id": subnet_id, "ip_address": ip}
        """

        result = {}
        neutron_port_list = self._neutron_list_ports()
        for p in neutron_port_list:
            port_id = p.get('id')
            result[port_id[:11]] = p
        return result

    def query_port_by_ip(self, ip):
        '''
        Query an port having the ip address
        :param ip: the ip address
        :return:
        '''
        neutron_port_list = self._neutron_list_ports()
        for p in neutron_port_list:
            for fixed_ip in p.get('fixed_ips'):
                if fixed_ip.get('ip_address') == ip:
                    return p
        return None

    def query_port_by_id(self, id_keyword=''):
        '''
        Query an port who's id has the keyword
        :param id_keyword: part string of the id string
        :return:
        '''
        neutron_port_list = self._neutron_list_ports()
        for p in neutron_port_list:
            if id_keyword in p.get('id'):
                return p
        return None

    def _neutron_list_ports(self, fresh=False):
        '''
        Return the neutron ports information in list, looks like
        [
            {
                u'status': u'ACTIVE',
                u'name': u'',
                u'allowed_address_pairs': [],
                u'admin_state_up': True,
                u'network_id': u'ea3928dc-b1fd-4a1a-940e-82b8c55214e6',
                u'tenant_id': u'3a55e7b5f5504649a2dfde7147383d02',
                u'extra_dhcp_opts': [],
                u'binding:vnic_type': u'normal',
                u'device_owner': u'network:dhcp',
                u'mac_address': u'fa:16:3e:83:95:fa',
                u'fixed_ips': [{u'subnet_id': u'94bf94c0-6568-4520-aee3-d12b5e472128', u'ip_address': u'10.0.0.3'}],
                u'id': u'13685e28-b09b-410c-8ecb-2deaeeb961b7',
                u'security_groups': [],
                u'device_id': u'dhcp1e6c17f8-6b90-567c-8d79-b06fc2608737-ea3928dc-b1fd-4a1a-940e-82b8c55214e6'
            },
        ]

        :param fresh: whether force to get the latest data
        :return: the neutron ports information in list
        '''
        result = []
        cache_file = '/tmp/_neutron_list_ports.cache'
        if not fresh and exists(cache_file):  # not require fresh, then read local cache
            if time() - getmtime(cache_file) < 30:  # the cache is updated within 30s
                try:
                    result = cPickle.load(open(cache_file, 'r'))
                except Exception:
                    return []
                return result
        if not self.neutron:
            return result
        try:
            result = self.neutron.list_ports().get('ports', [])
        except Exception:
            return None

        if result:  # only write in valid information
            cPickle.dump(result, open(cache_file, 'w'), True)
        return result


neutron_handler = NeutronHandler()

def show_port_info(keywords):
    '''

    :param keyword: might be the ip address or substring of the id string
    :return: related port
    '''
    for keyword in keywords.replace(',', ' ').split():
        port = neutron_handler.query_port_by_id(keyword) or \
               neutron_handler.query_port_by_ip(keyword)
        if port:
            output(color_str('b', '## port_id = %s\n' % (port.get('id'))))
            for k in port:
                output('%s: %s\n' %(k, port.get(k)))
        else:
            output('%s\n' %(color_str('r', 'No port is found, please '
                                           'check your tenant information')))


def get_port_id_from_ip(ip):
    """
    Return the port 11bit id from a given ip, or None.
    e.g., d4de9fe0-6d from 192.168.0.2
    """
    port = neutron_handler.query_port_by_ip(ip)
    if port:
        return port.get('id')[:11]
    return None