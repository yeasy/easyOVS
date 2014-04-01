__author__ = 'baohua'

from subprocess import call,Popen,PIPE

def get_neutron_ports():
        """
        Return the neutron port information, each line looks like
        qvoxxxx:{'id':id,'name':name,'mac':mac,"subnet_id": subnet_id, "ip_address": ip}
        """
        result={}
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
        return result
