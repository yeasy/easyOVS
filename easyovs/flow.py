__author__ = 'baohua'

from easyovs.log import output
from easyovs.util import compress_mac_str, color_str


class Flow(object):
    """
    An OpenvSwitch flow rule.
    """

    def __init__(self, bridge='', table=0, packet=0, priority=0, match='',
                 actions='', flow_id=0):
        self.bridge = bridge
        self.table = table
        self.packet = packet
        self.priority = priority
        self.match = match
        self.actions = actions
        self.id = flow_id
        self._format_str_ = '%-3u%-10u%-4u%-6u%-60s%-20s\n'
        # self.id, self.table, self.packet, self.priority, self.match,
        # self.actions

    @staticmethod
    def banner_output():
        output(color_str('%-3s%-10s%-4s%-6s%-60s%-20s\n'
               % ('ID', 'PKT', 'TAB', 'PRI', 'MATCH', 'ACT'), 'g'))

    def fmt_output(self):
        if self.packet > 0:
            result = \
                color_str( self._format_str_ % (self.id, self.packet,
                                                self.table,
                                                self.priority,
                                                compress_mac_str(self.match),
                                                self.actions), 'b')
        else:
            result = \
                self._format_str_ \
                % (self.id, self.packet, self.table,
                   self.priority, compress_mac_str(self.match), self.actions)
        output(result)

    def __eq__(self, other):
        return \
            self.table == other.table and self.priority == other.priority and \
            self.match == other.match and self.actions == other.actions

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return \
            self.table < other.table or \
            (self.table == other.table and self.priority > other.priority) or \
            (self.table == other.table and self.priority == other.priority
             and self.packet > 0 and other.packet ==0)

    def __lt__(self, other):
        return not self.__eq__(other) and not self.__gt__(other)
