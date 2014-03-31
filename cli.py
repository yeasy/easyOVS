__author__ = 'baohua'

from cmd import Cmd
from select import poll, POLLIN
import sys

from bridge import brDumpFlows,brIsExisted,brList,brDelFlow
from log import info, output, error
from util import colorStr


def checkArg(func):
    def wrapper(self,arg):
        if not arg:
            output('Argument is missed\n')
        else:
            func(self,arg)
    return wrapper

def checkBr(func):
    def wrapper(self,arg):
        if not brIsExisted(arg):
            output('The bridge does not exist.\n You can check available bridges using brshow\n')
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
        if arg and brIsExisted(arg):
            brDumpFlows(arg)
        elif self.bridge:
            brDumpFlows(self.bridge)
        else:
            output("Please give a valid bridge name.\n")

    def do_EOF( self, arg ):
        "Exit"
        output( '\n' )
        return self.do_exit(arg)

    def do_exit( self, _arg ):
        "Exit"
        return 'exited by user command\n'

    def do_help( self, line ):
        "Describe available CLI commands."
        Cmd.do_help( self, line )
        if line is '':
            output( self.helpStr )

    def do_list(self,_arg):
        '''
        Show available bridges in the system
        '''
        result = brList()
        output(result)

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
            self.prompt = colorStr('g', PROMPT_KW[:-2]+':%s> ' % arg)
            self.bridge = arg
            output('Default bridge is %s.\n' %self.bridge)

    def do_show(self,_arg):
        '''
        Show current default bridge
        '''
        if self.bridge:
            output('Default bridge is %s\n' %self.bridge)
        else:
            output('Default bridge is not set yet.\nPlease try <bridge> set.\n')

    def _delflow(self,bridge,flow_id):
        if not flow_id.isdigit():
            output('flow_id is not valid.\n')
            return
        if brIsExisted(bridge):
            if not brDelFlow(bridge,int(flow_id)):
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
                error( '*** Unknown command: %s: cmd=%s, bridge=%s, args=%s\n' % (line,cmd,bridge,args) )
        else:
            error( '*** Bridge %s is not existed\n' %bridge )