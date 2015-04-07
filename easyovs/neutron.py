__author__ = 'baohua'

from oslo.config import cfg

from easyovs import config
import keystoneclient.v2_0.client as ksclient
import neutronclient.v2_0.client as neutronclient
import sys

from os.path import exists, getmtime
from subprocess import Popen, PIPE
from time import time
import cPickle


def get_neutron_ports(fresh=False):
    """
    Return the neutron port information, each line looks like
    '583c7038-d3':{'id':id,'name':name,'mac_address':mac,"subnet_id":
    subnet_id, "ip_address": ip}
    """
    result = {}
    cache_file = '/tmp/tmp_neutron_port'
    if not fresh and exists(cache_file):  # not quite fresh, then try to read recent local cache
        if time() - getmtime(cache_file) < 30:  # the cache is updated within 60s
            try:
                result = cPickle.load(open(cache_file, 'r'))
            except Exception:
                return None
            return result
    try:
        cmd = 'neutron --os-auth-url %s --os-tenant-name %s --os-username %s ' \
              '--os-password %s port-list' % (cfg.CONF.OS.auth_url,
                                              cfg.CONF.OS.tenant_name,
                                              cfg.CONF.OS.username,
                                              cfg.CONF.OS.password)
        neutron_port_list = Popen(cmd, stdout=PIPE, stderr=PIPE,
                                  shell=True).stdout.read()
    except Exception:
        return None
    neutron_port_list = neutron_port_list.split('\n')
    if len(neutron_port_list) > 3:
        for i in range(3, len(neutron_port_list) - 1):
            l = neutron_port_list[i]
            if l.startswith('| '):
                l = l.strip(' |')
                l_value = map(lambda x: x.strip(), l.split('|'))
                if len(l_value) != 4:
                    continue
                else:
                    port_id, name, mac, ips = l_value
                    result[port_id[:11]] = {'id': port_id, 'name': name,
                                            'mac_address': mac}
                    result[port_id[:11]].update(eval(ips))
    if result:
        cPickle.dump(result, open(cache_file, 'w'), True)
    return result

class NeutronHandler(object):

    def __init__(self):
        config.init(sys.argv[1:])
        self.keystone = ksclient.Client(auth_url=cfg.CONF.OS.auth_url,
                               tenant_name=cfg.CONF.OS.tenant_name,
                               username=cfg.CONF.OS.username,
                               password=cfg.CONF.OS.password)
        self.token = self.keystone.auth_token
        neutron_endpoint_url = self.keystone.service_catalog.url_for(
            service_type='network')
        self.neutron = neutronclient.Client(endpoint_url=neutron_endpoint_url,
                                        token=self.token)

    def get_neutron_ports(self, fresh=False):
        """
        Return the neutron port information, each line looks like
        '583c7038-d3':{'id':id,'name':name,'mac':mac,"subnet_id": subnet_id, "ip_address": ip}
        """
        result = {}
        cache_file = '/tmp/tmp_neutron_port'
        if not fresh and exists(cache_file):  # not quite fresh, then try to read recent local cache
            if time() - getmtime(cache_file) < 30:  # the cache is updated within 60s
                try:
                    result = cPickle.load(open(cache_file, 'r'))
                except Exception:
                    return None
                return result
        try:
            neutron_port_list = self.neutron.list_ports().get('ports',[])
        except Exception:
            return None
        for p in neutron_port_list:
            port_id = p.get('id')
            result[port_id[:11]] = p
        if result:
            cPickle.dump(result, open(cache_file, 'w'), True)
        return result


neutron_handler = NeutronHandler()