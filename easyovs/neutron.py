__author__ = 'baohua'

from os.path import exists, getmtime
from subprocess import Popen, PIPE
from time import time
import cPickle


def get_neutron_ports(fresh=False):
    """
    Return the neutron port information, each line looks like
    first11bitid:{'id':id,'name':name,'mac':mac,"subnet_id": subnet_id, "ip_address": ip}
    """
    result = {}
    cache_file = '/tmp/tmp_neutron_port'
    if not fresh and exists(cache_file):  # not quite fresh, then try to read recent local cache
        if time() - getmtime(cache_file) < 60:  # the cache is updated within 60s
            try:
                result = cPickle.load(open(cache_file, 'r'))
            except Exception:
                return None
            return result
    try:
        neutron_port_list = Popen('neutron port-list', stdout=PIPE, stderr=PIPE, shell=True).stdout.read()
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
                    result[port_id[:11]] = {'id': port_id, 'name': name, 'mac': mac}
                    result[port_id[:11]].update(eval(ips))
    if result:
        cPickle.dump(result, open(cache_file, 'w'), True)
    return result


def get_port_id_from_ip(ip):
    """
    Return the port 11bit id from a given ip, or None.
    e.g., qvod4de9fe0-6d from 192.168.0.2
    """
    ports = get_neutron_ports()
    for k in ports:
        if ports[k]['ip_address'] == ip:
            return k
    return None
