__author__ = 'baohua'
from subprocess import PIPE, Popen
from easyovs.log import debug, error, output, warn
from easyovs.util import color_str

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

    def is_empty(self):
        """
        Check if this namespace is empty or only has lo
        """
        self._load()
        return not self.intfs or self.intfs.values()[0].get('intf') == 'lo'

    def show(self, test_content=None):
        """
        Show the namespace content in format
        """
        self._load(test_content)
        output(color_str("# Namespace = %s\n" % self.id, 'b'))
        if len(self.intfs) == 1 and 'lo' == self.intfs.values()[0].get('intf'):
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
                    intfs[id] = {'intf': intf, 'ip': [] }
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
        pass

    def find(self, pattern):
        """
        Find a namespace which have the pattern
        :param pattern: pattern to search
        :return:
        """
        ns = self._search_ns(pattern)
        if not ns:
            output('There is no ns matched.\n')
        else:
            self.show(ns)

    def list(self):
        """
        List existing namespaces in the system
        :return:
        """
        ns_list = self._get_ids()
        if not ns_list:
            warn('No namespace exists\n')
            return

        output(color_str('%d namespaces: ' % len(ns_list), 'b'))
        ns_list_valid = filter(lambda x: not NameSpace(x).is_empty(), ns_list)
        ns_list_empty = filter(lambda x: NameSpace(x).is_empty(), ns_list)
        if ns_list_valid:
            output(color_str('%s\n' % '\t'.join(ns_list), 'b'))
        if ns_list_empty:
            output('%s\n' % '\t'.join(ns_list))

    def show(self, id_prefix):
        """
        Show the content of specific id or id_prefix
        :param id_prefix: id of namespace to show
        :return:
        """
        ns_list = self._get_ids()
        if not ns_list:
            warn('No namespace exists\n')
            return
        for s in ns_list:
            if s.startswith(id_prefix):
                NameSpace(s).show()


    def _get_ids(self):
        """
        Get all ids of the namespaces
        :return: The list of namespace ids, e.g., ['red', 'blue']
        """
        run_cmd = '%s list' % self.ns_cmd
        spaces, err = Popen(run_cmd, stdout=PIPE, stderr=PIPE,
                            shell=True).communicate()
        if err:
            error("Failed to run %s, err=%s\n" % (run_cmd, err))
            return None
        ns_list = spaces.rstrip('\n').split('\n')
        ns_list.sort()
        return ns_list

    def _search_ns(self, pattern):
        """
        Find a namespace which have the pattern
        :param pattern: pattern to search
        :return: The id of the matched ns
        """
        ns_list = self._get_ids()
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
