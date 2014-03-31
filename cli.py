__author__ = 'baohua'

from cmd import Cmd
from select import poll, POLLIN
from subprocess import call,Popen,PIPE
import subprocess
import sys

from bridge import brDelFlow,brDumpFlows,brIsExisted,brList,brGetPorts
from log import info, output, error
from util import colorStr


def checkArg(func):
    def wrapper(self,arg):
        if not arg:
            output('Argument is missed\n')
        else:
            func(self,arg)
    return wrapper

PROMPT_KW='EasyOVS> '

class CLI( Cmd ):
    "Simple command-arg interface to talk to nodes."

    helpStr = (
        'The command format is: <bridge> command {args}\n'
        'For example:\n'
        '\tEasyOVS> br-int dump\n'
        '\n'
        'Default bridge can be set using\n\tset <bridge>.\n'
    )

    def __init__( self, bridge=None, stdin=sys.stdin, script=None ):
        self.prompt = colorStr('g',PROMPT_KW)
        self.bridge = bridge
        self.stdin = stdin
        self.inPoller = poll()
        self.inPoller.register( stdin )
        Cmd.__init__( self )
        info( '*** Starting CLI:\n' )
        while True:
            try:
                #if self.isatty():
                    #quietRun( 'stty sane' )
                self.cmdloop()
                break
            except KeyboardInterrupt:
                info( '\nInterrupt\n' )

    def do_delflow(self,arg):
        '''
        [bridge] delflow flow_id
        Del a flow from a bridge.
        '''
        if len(arg.split())==2:
            self._delflow(arg.split()[0],arg.split()[1])
        elif len(arg.split())==1 and self.bridge:
            self._delflow(self.bridge,arg)
        else:
            output("Please use [bridge] delflow flow_id.\n")

    def do_dump(self,arg):
        '''
        [bridge] dump
        Dump the flows from a bridge.
        '''
        if arg:
            brDumpFlows(arg)
        elif self.bridge:
            brDumpFlows(self.bridge)
        else:
            output("Please give a valid bridge.\n")

    def do_EOF( self, arg ):
        "Exit"
        output( '\n' )
        return self.do_exit(arg)

    def do_exit( self, _arg ):
        "Exit"
        return 'exited by user command\n'

    def do_get(self,_arg):
        '''
        Get current default bridge
        '''
        if self.bridge:
            output('Default bridge is %s\n' %self.bridge)
        else:
            output('Default bridge is not set yet.\nPlease try <bridge> set.\n')

    def do_help( self, line ):
        "Describe available CLI commands."
        Cmd.do_help( self, line )
        if line is '':
            output( self.helpStr )

    def do_list(self,_arg):
        '''
        Show available bridges in the system
        '''
        bridges = brList()
        br_info = ''
        for br in sorted(bridges.keys()):
            br_info += "%s\n" %(br)
            if bridges[br]['Port']:
                br_info += " Port:\t\t%s\n"  %(' '.join(bridges[br]['Port'].keys()))
            if bridges[br]['Controller']:
                br_info += " Controller:\t%s\n"  %(' '.join(bridges[br]['Controller']))
            if bridges[br]['fail_mode']:
                br_info += " Fail_Mode:\t%s\n"  %(bridges[br]['fail_mode'])
        output(br_info)

    def do_quit( self, line ):
        "Exit"
        return self.do_exit( line )

    def do_set( self, arg ):
        '''
        <bridge> set
        Set the default bridge
        '''
        if not arg:
            output('Argument is missed\n')
        elif not brIsExisted(arg):
            output('The bridge does not exist.\n You can check available bridges using show\n')
        else:
            self.prompt = colorStr('g', PROMPT_KW[:-2]+':%s> ' % colorStr('b',arg))
            self.bridge = arg
            output('Default bridge is %s.\n' %self.bridge)

    def do_sh( self, line ):
        "Run an external shell command"
        call( line, shell=True )

    def do_show(self,arg):
        '''
        Show details of a bridge.
        '''
        if arg:
            br = arg
        elif self.bridge:
            br = self.bridge
        else:
            output("Please give a valid bridge.\n")
            return
        ovs_ports = brGetPorts(br)
        output('%s\n' %br)
        neutron_ports = self.get_neutron_ports()
        output('%-20s%-12s%-8s%-12s' %('Intf','Port','Tag','Type'))
        if neutron_ports:
            output('%-16s%-24s\n' %('vmIP','vmMAC'))
        else:
            output('\n')
        content=[]
        for intf in ovs_ports:
            port,tag,type = ovs_ports[intf]['port'],ovs_ports[intf]['tag'],ovs_ports[intf]['type']
            if neutron_ports and intf in neutron_ports:
                vmIP, vmMac = neutron_ports[intf]['ip_address'],neutron_ports[intf]['mac']
            else:
                vmIP,vmMac = '', ''
            content.append((intf,port,tag,type,vmIP,vmMac))
            #output('%-20s%-8s%-16s%-24s%-8s\n' %(intf,port,vmIP,vmMac,tag))
        content.sort(key=lambda x:x[0])
        content.sort(key=lambda x:x[3])
        for _ in content:
            output('%-20s%-12s%-8s%-12s' %(_[0],_[1],_[2],_[3]))
            if neutron_ports:
                output('%-16s%-24s\n' %(_[4],_[5]))
            else:
                output('\n')

    def get_neutron_ports(self):
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

    def _delflow(self,bridge,flow_id):
        if not flow_id.isdigit():
            output('flow_id is not valid.\n')
        elif not brDelFlow(bridge,int(flow_id)):
            output('Delflow %u from %s failed.\n' %(int(flow_id),bridge))

    def emptyline( self ):
        "Don't repeat last command when you hit return."
        pass

    def default(self,line):
        #bridge, cmd, line = self.parseline( line )
        if len(line.split()) != 2 and len(line.split()) !=3:
            error( '*** Unknown command: %s\n' % line )
            return
        bridge,cmd,args='','',''
        if len(line.split()) == 2:
            bridge,cmd = line.split()
        else:
            bridge,cmd,args = line.split()[0],line.split()[1],line.split()[2]
        if brIsExisted(bridge):
            try:
                if args:
                    getattr(self,'do_%s' %(cmd))(' '.join([bridge,args]))
                else:
                    getattr(self,'do_%s' %(cmd))(bridge)
            except AttributeError:
                error( '*** Unknown command: %s, cmd=%s, bridge=%s, args=%s\n' % (line,cmd,bridge,args) )
        else:
            error( '*** Bridge %s is not existed\n' %bridge )