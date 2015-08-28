__author__ = 'baohua'
from subprocess import PIPE, Popen
from easyovs.log import debug, error, output, warn
from easyovs.util import color_str, b, r

# id intf mac ips
_format_str_ns_intf_ = '%-6s%-18s%-20s%-20s\n'


#deprecated
class NameSpace(object):
    """
    represent one network namespace
    """
    def __init__(self, id):
        self.id = id
        self.ns_cmd = 'ip netns'
        self.intfs = {}
        self._load()

    def is_empty(self):
        """
        Check if this namespace is empty or only has lo
        """
        return (not self.intfs) or \
               (len(self.intfs) == 1 and
                self.intfs.values()[0].get('intf') == 'lo')

    def has_intf(self, intf_name):
        """
        Check if this namespace has the intf.
        """
        for i in self.intfs:
            if self.intfs[i]['intf'] == intf_name:
                return True
        return False

    def find_intf(self, pattern):
        """
        Return the first matched {'intf': eth0, 'ip': [ip1, ip2], 'mac': xxx }
        """
        for i in self.intfs:
            if pattern in self.intfs[i]['intf']:
                return self.intfs[i]
        return None

    def find_intfs(self, pattern):
        """
        Return the matched list [{'intf': eth0, 'ip': [ip1, ip2], 'mac': xxx }]
        """
        result = []
        for i in self.intfs:
            if pattern in self.intfs[i]['intf']:
                result.append(self.intfs[i])
        return result

    def get_intf_by_name(self, name):
        """
        Return {'intf': eth0, 'ip': [ip1, ip2], 'mac': xxx }
        """
        for i in self.intfs:
            if self.intfs[i]['intf'] == name:
                return self.intfs[i]
        return None

    def get_intfs(self):
        """
        Return {'1':{'intf': eth0, 'ip': [ip1, ip2], 'mac': xxx }}
        """
        return self.intfs

    def get_ip_of_intf(self, name):
        """
        Return  the list of ips for the interface
        """
        if self.intfs:
            for i in self.intfs:
                if self.intfs[i]['intf'] == name:
                    return self.intfs[i]['ip']
        return None

    def show_routes(self):
        """
        """
        run_cmd = '%s exec %s route -en' % (self.ns_cmd, self.id)
        result, err = Popen(run_cmd, stdout=PIPE, stderr=PIPE,
                             shell=True).communicate()
        if err:
            error("Failed to run %s, err=%s\n" % (run_cmd, err))
        else:
            output(result)

    def show(self, test_content=None):
        """
        Show the namespace content in format
        """
        self._load(test_content)
        output(b("# Namespace = %s\n" % self.id))
        if self.is_empty():
            output('Only lo interface existed\n')
            return
        output(_format_str_ns_intf_ %('ID', 'Intf', 'Mac', 'IPs'))
        for d in self.intfs:
            if self.intfs[d].get('intf') != 'lo':
                output(_format_str_ns_intf_
                       % ( d, self.intfs[d].get('intf'),
                           self.intfs[d].get('mac'),
                           ', '.join(self.intfs[d].get('ip'))))

    def _load(self, test_content=None):
        if not test_content: # test_content is null
            run_cmd = '%s exec %s ip a' % (self.ns_cmd, self.id)
            content, err = Popen(run_cmd, stdout=PIPE, stderr=PIPE,
                                 shell=True).communicate()
            if err:
                error("Failed to run %s, err=%s\n" % (run_cmd, err))
                return
        else:
            content = test_content

        lines = content.split('\n')
        intfs = {}  #  {'1':{'intf': eth0, 'ip': [ip1, ip2]}, 'mac': xxx }
        for l in lines:
            if not l:
                continue
            if not l.startswith(' '):  # one interface: 1: lo: xxxxx
                intf_line = l.split(':')
                if len(intf_line) < 2:
                    warn('Seems the interface line too short\n')
                    continue
                else:
                    id = intf_line[0].strip()
                    intf = intf_line[1].strip()
                    intfs[id] = {'intf': intf, 'ip': [], 'mac': '*' }
            else:  # some content line
                cons = l.split()
                if len(cons) < 2:
                    continue
                if cons[0] == 'inet':
                    intfs[id]['ip'].append(cons[1])
                elif cons[0] == 'link/ether':
                    intfs[id]['mac'] = cons[1]
        self.intfs = intfs


class NameSpaces(object):
    """
    represent the network namespaces in the system
    """
    def __init__(self):
        self.ns_cmd = 'ip netns'
        self.ns_ids = []

    def get_ns_by_port(self, intf_name):
        """
        Find the first namespace who has the interface
        :param intf_name:
        :return:
        """
        ns_list = self.get_ids()
        for ns in ns_list:
            if NameSpace(ns).has_intf(intf_name):
                return ns
        return None

    def find(self, pattern):
        """
        Find a namespace which have the pattern
        :param pattern: pattern to search
        :return: N/A
        """
        ns = self._search_ns(pattern)
        if not ns:
            output('There is no ns matched.\n')
        else:
            self.show(ns)

    def route(self, id_pattern):
        """
        Show routes of a namespace whose id matched
        :param id_pattern: id pattern to match
        :return: N/A
        """
        ns_list = self.get_ids()
        if not ns_list:
            warn('No namespace exists\n')
            return
        for s in ns_list:
            if id_pattern in s:
                NameSpace(s).show_routes()

    def clean(self):
        """
        Clean all empty namespaces
        :return:
        """
        output('Cleaning empty namespaces...\n')
        num_empty = 0
        for ns in self.get_ids():
            if NameSpace(ns).is_empty():
                run_cmd = '%s delete %s' % (self.ns_cmd, ns)
                spaces, err = Popen(run_cmd, stdout=PIPE, stderr=PIPE,
                                    shell=True).communicate()
                if err:
                    error("Failed to run %s, err=%s\n" % (run_cmd, err))
                else:
                    num_empty += 1
        output('%d empty namespaces cleaned\n' % num_empty)


    def list(self):
        """
        List existing namespaces in the system
        :return:
        """
        ns_list = self.get_ids()
        if not ns_list:
            output('No namespace exists\n')
            return
        output(b('%d namespaces:\n' % len(ns_list)))
        ns_list_valid = filter(lambda x: not NameSpace(x).is_empty(), ns_list)
        if ns_list_valid:
            output(b('%d valid namespaces:\n' % len(ns_list_valid)))
            output('%s\n' % '\t'.join(ns_list_valid))
        ns_list_empty = [e for e in ns_list if e not in ns_list_valid]
        if ns_list_empty:
            output(b('%d empty namespaces:\n' % len(ns_list_empty)))
            if len(ns_list_empty) > 4:
                output(r('%s\n' % '\t'.join(ns_list_empty[:4])))
            else:
                output(r('%s\n' % '\t'.join(ns_list_empty)))

    def show(self, id_pattern):
        """
        Show the content of specific id or id_pattern
        :param id_pattern: id of namespace to show
        :return:
        """
        ns_list = self.get_ids()
        if not ns_list:
            warn('No namespace exists\n')
            return
        for s in ns_list:
            if id_pattern in s:
                NameSpace(s).show()
                return

    def get_ids(self):
        """
        Get all ids of the namespaces
        :return: The list of namespace ids, e.g., ['red', 'blue']
        """
        if self.ns_ids:
            return self.ns_ids
        run_cmd = '%s list' % self.ns_cmd
        spaces, err = Popen(run_cmd, stdout=PIPE, stderr=PIPE,
                            shell=True).communicate()
        if err:
            error("Failed to run %s, err=%s\n" % (run_cmd, err))
            return []
        if not spaces:  # spaces == ''
            return []
        ns_list = spaces.rstrip('\n').split('\n')
        ns_list.sort()
        self.ns_ids = ns_list
        return ns_list

    def _search_ns(self, pattern):
        """
        Find a namespace which have the pattern
        :param pattern: pattern to search
        :return: The id of the matched ns
        """
        ns_list = self.get_ids()
        if not ns_list:
            return None
        for ns in ns_list:  # qrouter-03266ec4-a03b-41b2-897b-c18ae3279933
            run_cmd = '%s exec %s ip addr | grep %s' % (self.ns_cmd, ns,
                                                        pattern)
            result, err = Popen(run_cmd, stdout=PIPE, stderr=PIPE,
                                shell=True) .communicate()
            if err:
                warn("Failed to run %s, err=%s\n" % (run_cmd, err))
                continue
            if result:
                return ns
        return None


if __name__ == '__main__':
    n = NameSpaces()
    n.list()
    n.show('r')
    n.find('127')

    t = '''1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host
       valid_lft forever preferred_lft forever
12: tapd41cd120-62: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN
    link/ether fa:16:3e:75:01:0e brd ff:ff:ff:ff:ff:ff
    inet 11.3.3.2/24 brd 11.3.3.255 scope global tapd41cd120-62
       valid_lft forever preferred_lft forever
    inet 169.254.169.254/16 brd 169.254.255.255 scope global tapd41cd120-62
       valid_lft forever preferred_lft forever
    inet6 fe80::f816:3eff:fe75:10e/64 scope link
       valid_lft forever preferred_lft forever
       '''
    NameSpace('id').show(t)
