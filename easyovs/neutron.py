__author__ = 'baohua'

from os.path import exists,getmtime
from subprocess import call,Popen,PIPE
from time import  time
import cPickle as pickle


def get_neutron_ports(fresh=False):
        """
        Return the neutron port information, each line looks like
        qvoxxxx:{'id':id,'name':name,'mac':mac,"subnet_id": subnet_id, "ip_address": ip}
        """
        result={}
        cache_file='/tmp/tmp_neutron_port'
        if not fresh and exists(cache_file): #not quite fresh, then try to read local cache
            if time()-getmtime(cache_file) < 60: #the cache is updated within 60s
                try:
                    result = pickle.load(open(cache_file, 'r'))
                except Exception:
                    return None
                return result
        try:
            neutron_port_list= Popen('neutron port-list', stdout=PIPE,stderr=PIPE,shell=True).stdout.read()
        except Exception:
            return None
        neutron_port_list = neutron_port_list.split('\n')
        if len(neutron_port_list)>3:
            for i in range(3,len(neutron_port_list)-1):
                l = neutron_port_list[i]
                if l.startswith('| '):
                    l = l.strip(' |')
                    l_value=map(lambda x: x.strip(),l.split('|'))
                    if len(l_value) !=4:
                        continue
                    else:
                        id,name,mac,ips = l_value
                        result['qvo'+id[:11]] = {'id':id,'name':name,'mac':mac}
                        result['qvo'+id[:11]].update(eval(ips))
        if result:
            pickle.dump(result, open(cache_file, 'w'),True)
        return result
