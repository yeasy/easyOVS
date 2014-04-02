__author__ = 'baohua'

from easyovs.log import output

_format_str_ = '%-3s%-4s%-10s%-6s%-60s%-20s\n'


class Flow(object):
    """
    An OpenvSwitch flow rule.
    """

    def __init__(self, bridge=None, table=0, packet=0, priority=None, match=None, actions=None, id=0):
        self.bridge = bridge
        self.table = table
        self.packet = packet
        self.priority = priority
        self.match = match
        self.actions = actions
        self.id = id

    @staticmethod
    def bannerOutput():
        output(_format_str_ % ('ID', 'TAB', 'PKT', 'PRI', 'MATCH', 'ACT'))

    def fmtOutput(self):
        output(_format_str_ % (self.id, self.table, self.packet, self.priority,\
                               self.match.replace('_port', '').replace('_tci','').replace('dl_vlan','vlan'),
                               self.actions))

    def __eq__(self, other):
        return self.table == other.table and \
               self.priority == other.priority and \
               self.match == other.match and \
               self.actions == other.actions

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
