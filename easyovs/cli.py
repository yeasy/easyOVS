__author__ = 'baohua'

from cmd import Cmd
try:
    from oslo_config import cfg
except ImportError:
    from oslo.config import cfg
from select import poll
from subprocess import call
import sys

from easyovs.bridge_ctrl import br_addflow, br_delbr, br_addbr, br_delflow, \
    br_dump, br_exists,br_list, br_show
from easyovs.iptables import show_iptables_rules
from easyovs.log import info, output, error, debug
from easyovs.neutron import show_port_info
from easyovs.util import color_str, fmt_flow_str


PROMPT_KW = 'EasyOVS> '


def check_arg(func):
    def wrapper(self, arg):
        if not arg:
            output('Argument is missed\n')
        else:
            func(self, arg)
    return wrapper


class CLI(Cmd):
    """
    Simple command-arg interface to talk to nodes.
    """

    helpStr = (
        'The command format is: <bridge> command {args}\n'
        'For example:\n'
        '\tEasyOVS> br-int dump\n'
        '\n'
        'Default bridge can be set using\n\tset <bridge>.\n'
    )

    def __init__(self, bridge=None, stdin=sys.stdin):
        self.prompt = color_str('g', PROMPT_KW)
        self.bridge = bridge
        self.stdin = stdin
        self.in_poller = poll()
        self.in_poller.register(stdin)
        Cmd.__init__(self)
        output("***\n Welcome to EasyOVS,"
               "type help to see available commands.\n***\n")
        info('*** Starting CLI:\n')
        debug("==cfg.ADMIN==\n")
        debug("auth_url = %s\n" % cfg.CONF.OS.auth_url)
        debug("username = %s\n" % cfg.CONF.OS.username)
        debug("password = %s\n" % cfg.CONF.OS.password)
        debug("tenant_name = %s\n" % cfg.CONF.OS.tenant_name)
        while True:
            try:
                #if self.isatty():
                #quietRun( 'stty sane' )
                self.cmdloop()
                break
            except KeyboardInterrupt:
                info('\nInterrupt\n')

    def do_addflow(self, arg):
        """
        addflow [bridge] flow
        Add a flow to a bridge.
        """
        args = arg.replace('"', '').replace("'", "").split()
        if len(args) < 2:
            output('Not enough parameters are given, use like ')
            output('br-int addflow priority=3 ip actions=OUTPUT:1\n')
            return
        bridge, flow_str = args[0], ' '.join(args[1:])
        if not br_exists(bridge) and self.bridge:
            bridge, flow_str = self.bridge, ' '.join(args)
        else:
            output('Please give a valid bridge.\n')
            return
        flow = fmt_flow_str(flow_str)
        if not flow:
            output('Please give a valid flow.\n')
            return
        if not br_addflow(bridge, flow):
            output('Add flow <%s> to %s failed.\n' % (flow, bridge))
        else:
            output('Add flow <%s> to %s done.\n' % (flow, bridge))

    def do_delflow(self, arg):
        """
        [bridge] delflow flow_id
        Del a flow from a bridge.
        """
        args = arg.split()
        if len(args) >= 2:
            flow_ids = ' '.join(args[1:]).replace(',', ' ').split()
            if not br_delflow(args[0], flow_ids):
                output('Del flow#%s from %s failed.\n'
                       % (' '.join(flow_ids), args[0]))
            else:
                output('Del flow#%s from %s done.\n'
                       % (','.join(flow_ids), args[0]))
        elif len(args) == 1 and self.bridge:
            if not br_delflow(self.bridge, arg):
                output('Del flow#%s from %s failed.\n'
                       % (arg, self.bridge))
            else:
                output('Del flow#%s from %s done.\n' % (arg, self.bridge))
        else:
            output("Please use like [bridge] delflow flow_id.\n")

    def do_addbr(self, arg):
        """
        addbr [bridge]
        create a new bridge with name
        """
        args = arg.split()
        if len(args) < 1:
            output('Not enough parameters are given, use like ')
            output('addbr br1,br2\n')
            return
        brs = ' '.join(args[1:]).replace(',', ' ').split()
        for br in brs:
            br_addbr(br)

    def do_delbr(self, arg):
        """
        delbr [bridge]
        Delete a bridge
        """
        args = arg.split()
        if len(args) < 1:
            output('Not enough parameters are given, use like ')
            output('del br1,br2\n')
            return
        brs = ' '.join(args[1:]).replace(',', ' ').split()
        for br in brs:
            br_delbr(br)

    def do_dump(self, arg):
        """
        [bridge] dump
        Dump the flows from a bridge.
        """
        if arg:
            br_dump(arg)
        elif self.bridge:
            br_dump(self.bridge)
        else:
            output("Please give a valid bridge.\n")
            return

    def do_EOF(self, arg):
        """
        Exit.
        """
        output('\n')
        return self.do_quit(arg)

    def do_exit(self, _arg):
        """
        Go up one level in the command mode structure. If
        already at the top level, exit from the command line
        interface and log out.
        """
        if self.bridge:
            self.bridge = None
            self.prompt = color_str('g', PROMPT_KW)
        else:
            return self.do_quit(_arg)

    def do_get(self, _arg):
        """
        Get current default bridge.
        """
        if self.bridge:
            output('Current default bridge is %s\n' % self.bridge)
        else:
            output('Default bridge is not set yet.\nPlease try <bridge> set.\n')

    def do_help(self, line):
        """
        Describe available CLI commands.
        """
        Cmd.do_help(self, line)
        if line is '':
            output(self.helpStr)

    def do_ipt(self, line):
        """
        Show the iptables rules of a given vm.
        """
        show_iptables_rules(line)

    def do_query(self, line):
        """
        Show the port information of given keywords.
        """
        show_port_info(line)

    def do_list(self, _arg):
        """
        List available bridges in the system.
        """
        br_list()

    def do_quit(self, line):
        """
        Exit
        """
        output('***\n Quit by user command.***\n')
        return True

    def do_set(self, arg):
        """
        <bridge> set
        Set the default bridge
        """
        if not arg:
            output('Argument is missed\n')
        elif not br_exists(arg):
            output('The bridge does not exist.\n '
                   'You can check available bridges using show\n')
        else:
            self.prompt = \
                color_str('g', PROMPT_KW[:-2] + ':%s> ' % color_str('b', arg))
            self.bridge = arg
            output('Set the default bridge to %s.\n' % self.bridge)

    def do_sh(self, line):
        """
        Run an external shell command.
        """
        call(line, shell=True)

    def do_show(self, arg):
        """
        Show port details of a bridge, with neutron information.
        """
        if arg:
            br_show(arg)
        elif self.bridge:
            br_show(self.bridge)
        else:
            output("Please give a valid bridge.\n")
            return

    def emptyline(self):
        """
        Don't repeat last command when you hit return.
        """
        pass

    def default(self, line):
        #bridge, cmd, line = self.parseline( line )
        if len(line.split()) < 2:
            error('*** Unknown command: %s ***\n' % line)
            return
        bridge, cmd, args = '', '', ''
        if len(line.split()) == 2:
            bridge, cmd = line.split()
        else:
            bridge, cmd, args = \
                line.split()[0], line.split()[1], ' '.join(line.split()[2:])
        if br_exists(bridge):
            try:
                if args:
                    getattr(self, 'do_%s' % cmd)(' '.join([bridge, args]))
                else:
                    getattr(self, 'do_%s' % cmd)(bridge)
            except AttributeError:
                error('*** Unknown command: '
                      '%s, cmd=%s, bridge=%s, args=%s '
                      '***\n' % (line, cmd, bridge, args))
        else:
            error('*** Bridge %s is not existed\n' % bridge)
