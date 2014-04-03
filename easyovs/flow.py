__author__ = 'baohua'

from easyovs.log import output


class Flow(object):
    """
    An OpenvSwitch flow rule.
    """

    def __init__(self, bridge='', table='', packet='', priority='', match='', actions='', flow_id=0):
        self.bridge = bridge
        self.table = table
        self.packet = packet
        self.priority = priority
        self.match = match
        self.actions = actions
        self.id = flow_id
        self._format_str_ = '%-3u%-4s%-10s%-6s%-60s%-20s\n'

    @staticmethod
    def banner_output():
        output('%-3s%-4s%-10s%-6s%-60s%-20s\n'
               % ('ID', 'TAB', 'PKT', 'PRI', 'MATCH', 'ACT'))

    def fmt_output(self):
        output(self._format_str_ % (self.id, self.table, self.packet, self.priority,
                               self.match.replace('_port', '').replace('_tci', '').replace('dl_vlan', 'vlan'),
                               self.actions))

    def __eq__(self, other):
        return self.table == other.table and self.priority == other.priority and\
               self.match == other.match and self.actions == other.actions

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return self.table < other.table or \
               (self.table == other.table and self.priority > other.priority) or \
               (self.table == other.table and self.priority == other.priority and len(self.match) > len(other.match))

    def __lt__(self, other):
        return self.table > other.table or \
               (self.table == other.table and self.priority < other.priority) or \
               (self.table == other.table and self.priority == other.priority and len(self.match) < len(other.match))
