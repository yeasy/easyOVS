__author__ = 'baohua'

from cmd import Cmd
try:
    from oslo_config import cfg
except ImportError:
    from oslo.config import cfg
from select import poll
from subprocess import call
import os
import sys

from easyovs import VERSION
from easyovs.bridge_ctrl import br_addflow, br_delbr, br_addbr, br_delflow, \
    br_dump, br_exists, br_list, br_show
from easyovs.common import CMDS_ONE, CMDS_BR, CMDS_OTHER
from easyovs.iptables import IPtables
from easyovs.log import info, output, error, debug, warn
from easyovs.neutron import query_info
from easyovs.util import color_str, fmt_flow_str
from easyovs.namespaces import NameSpaces
from easyovs.dvr import DVR


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

    def __init__(self, stdin=sys.stdin, foreground=True):
        self.bridge = None  # default bridge
        self.ipt = None
        self.nss = None
        self.dvr = None
        if foreground:
            self.prompt = color_str(PROMPT_KW, 'g')
            self.stdin = stdin
            self.in_poller = poll()
            self.in_poller.register(stdin)
            Cmd.__init__(self)
            output("***\n Welcome to EasyOVS %s, "
                   "type help to see available cmds.\n***\n" % VERSION)
            info('*** Starting CLI:\n')
            debug("==Loading credentials==\n")
            debug("auth_url = %s\n" % os.getenv('OS_AUTH_URL') or
                  cfg.CONF.OS.auth_url)
            debug("username = %s\n" % os.getenv('OS_USERNAME') or
                  cfg.CONF.OS.username)
            passwd = os.getenv('OS_PASSWORD') or cfg.CONF.OS.password
            passwd = passwd[:len(passwd)/4] + "****" + passwd[-len(passwd)/4:]
            debug("password = %s\n" % passwd)
            debug("tenant_name = %s\n" % os.getenv('OS_TENANT_NAME') or
                  cfg.CONF.OS.tenant_name)
            while True:
                try:
                    #if self.isatty():
                    #quietRun( 'stty sane' )
                    self.cmdloop()
                    break
                except KeyboardInterrupt:
                    info('\nInterrupt\n')

    def do_addflow(self, arg, forced=False):
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
        if not br_exists(bridge):
            if self.bridge:
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

    def do_delflow(self, arg, forced=False):
        """
        [bridge] delflow flow_id, flow_id
        Del a flow from a bridge.
        :param args:
        """
        args = arg.split()
        if len(args) >= 2:
            flow_ids = ' '.join(args[1:]).replace(',', ' ').split()
            if not br_delflow(args[0], flow_ids, forced):
                output('Del flow#%s from %s failed.\n'
                       % (' '.join(flow_ids), args[0]))
            else:
                output('Del flow#%s from %s done.\n'
                       % (','.join(flow_ids), args[0]))
        elif len(args) == 1 and self.bridge:
            if not br_delflow(self.bridge, arg, forced):
                output('Del flow#%s from %s failed.\n'
                       % (arg, self.bridge))
            else:
                output('Del flow#%s from %s done.\n' % (arg, self.bridge))
        else:
            output("Please use like [bridge] delflow flow_id.\n")

    def do_addbr(self, arg, forced=False):
        """
        addbr br1, br2
        create a new bridge with name
        """
        brs = arg.replace(',', ' ').split()
        if len(brs) < 1:
            output('Not enough parameters are given, use like ')
            output('addbr br1,br2\n')
            return
        for br in brs:
            br_addbr(br)

    def do_delbr(self, arg, forced=False):
        """
        delbr br1, br2
        Delete a bridge
        """
        brs = arg.replace(',', ' ').split()
        if len(brs) < 1:
            output('Not enough parameters are given, use like ')
            output('delbr br1,br2\n')
            return
        for br in brs:
            br_delbr(br)

    def do_dump(self, arg, forced=False):
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
            self.prompt = color_str(PROMPT_KW, 'g')
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

    def do_dvr(self, arg):
        """
        Check the dvr rules
        dvr [check]
        dvr check compute
        dvr check net
        """
        args = arg.split()
        if len(args) > 2:  # only 1 is valid
            warn("Not correct parameters, use as:\n")
            warn("dvr [check]\n")
            warn("dvr check compute\n")
            warn("dvr check net\n")
            return
        self.dvr = DVR()
        if len(args) == 0:  # default cmd for ns
            args.insert(0, 'check')
        cmd = args[0]
        if not hasattr(self.dvr, '%s' % cmd):
            error('Unsupported cmd=%s\n' % cmd)
            return
        if cmd == 'check':
            if len(args) == 1:  # only check cmd is given
                debug('run self.dvr.%s()\n' % cmd)
                getattr(self.dvr, '%s' % cmd)()
            else:  # node parameter is given
                debug('run self.dvr.%s(%s)\n' % (cmd, args[1]))
                getattr(self.dvr, '%s' % cmd)(args[1])

    def do_ipt(self, arg):
        """
        Show the iptables rules, e.g.,
        ipt vm vm1,vm2
        ipt show nat,raw,filter [INPUT]
        ipt check nat,raw,filter
        """
        args = arg.split()
        if len(args) < 1 or len(args) > 3:  # only 1-3 is valid
            warn("Not correct parameters, use as:\n")
            warn("ipt vm vm_ip\n")
            warn("ipt show|check [filter] [INPUT]\n")
            return
        self.ipt = IPtables()
        cmd = args[0]
        if not hasattr(self.ipt, '%s' % cmd):
            error('Unsupported cmd=%s\n' % cmd)
            return
        if cmd == 'vm':
            if len(args) == 1:
                error('No vm ip is given\n')
                return
            else:
                for vm_ip in args[1:]:
                    debug('run self.ipt.%s(%s)\n' % (cmd, vm_ip))
                    getattr(self.ipt, '%s' % cmd)(vm_ip)
        elif cmd in ['check', 'show']:
            ns = None
            if args[-1] in NameSpaces().get_ids():
                ns = args.pop()
            if len(args) == 1:  # show
                debug('run self.ipt.%s(ns=%s)\n' % (cmd, ns))
                getattr(self.ipt, '%s' % cmd)(ns=ns)
                return
            elif len(args) == 2:  # filter|INPUT
                if args[1] in self.ipt.get_valid_tables():  # filter
                    debug('run self.ipt.%s(table=%s,ns=%s)\n' % (cmd,
                                                                 args[1], ns))
                    getattr(self.ipt, '%s' % cmd)(table=args[1], ns=ns)
                else:  # INPUT
                    debug('run self.ipt.%s(chain=%s, ns=%s)\n'
                          % (cmd, args[1], ns))
                    getattr(self.ipt, '%s' % cmd)(chain=args[1], ns=ns)
            elif len(args) == 3:
                if args[1] in self.ipt.get_valid_tables():  # filter INPUT
                    debug('run self.ipt.%s(table=%s, chain=%s, ns=%s\n)'
                          % (cmd, args[1], args[2], ns))
                    getattr(self.ipt, '%s' % cmd)(table=args[1],
                                                  chain=args[2], ns=ns)
                else:
                    warn("Unknown table, table=%s\n" % args[1])

    def do_ns(self, arg):
        """
        Show the network namespace content, e.g.,
        ns list
        ns show id_prefix
        ns find pattern
        """
        args = arg.split()
        if len(args) > 2:  # only 1-2 is valid
            warn("Not correct parameters, use as:\n")
            warn("ns [list]\n")
            warn("ns show id_prefix (lo intf is ignored)\n")
            warn("ns find pattern\n")
            return
        self.nss = NameSpaces()
        if len(args) == 0:  # default cmd for ns
            args.insert(0, 'list')
        cmd = args[0]
        if not hasattr(self.nss, '%s' % cmd):
            error('Unsupported cmd=%s\n' % cmd)
            return
        if cmd in ['list', 'clean']:
            if len(args) != 1:
                error('No param should be given\n')
                return
            else:
                debug('run self.nss.%s()\n' % cmd)
                getattr(self.nss, '%s' % cmd)()
        elif cmd in ['show', 'find', 'route']:
            if len(args) == 2:  #
                debug('run self.nss.%s(%s)\n' % (cmd, args[1]))
                getattr(self.nss, '%s' % cmd)(args[1])
            else:
                warn("Invalid param number, no reach here, %s\n" % arg)
                return
        else:
            error("Unknown cmd, cmd= %s\n" % arg)

    def do_query(self, line):
        """
        Show the port information of given keywords.
        """
        query_info(line)

    def do_list(self, _arg=None):
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
                color_str(PROMPT_KW[:-2] + ':%s> ' % color_str('b', arg), 'g')
            self.bridge = arg
            output('Set the default bridge to %s.\n' % self.bridge)

    def do_sh(self, line):
        """
        Run an external shell command.
        """
        call(line, shell=True)

    def do_show(self, arg, forced=False):
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

    def run(self, cmd, forced=False):
        '''
        Run given commands from -m 'xxxx'. Treat this similar with CLI.
        :param args:
        :param forced:
        :return:
        '''
        cmd_split = cmd.split()
        if cmd_split[0] in CMDS_ONE:  # list
            func = cmd_split[0]
            getattr(self, 'do_' + func)()
        elif cmd_split[0] in CMDS_BR:
            if len(cmd_split) > 2:  # e.g., delflow br0 9,10
                func, args = cmd_split[0], ' '.join(cmd_split[1:])
                debug("run do_%s(%s, %s)\n" %
                      (func, args.replace(',', ' '), forced))
                getattr(self, 'do_' + func)(args.replace(',', ' '), forced)
            else:  # e.g., delbr br0
                func, args = cmd_split[0], cmd_split[1]
                getattr(self, 'do_' + func)(args)
        elif cmd_split[0] in CMDS_OTHER:  # e.g., ipt vm 10.0.0.1, 10.0.0.2
            func, args = cmd_split[0], ' '.join(cmd_split[1:])
            getattr(self, 'do_' + func)(args)
        else:
            output('Wrong command format is given\n')
