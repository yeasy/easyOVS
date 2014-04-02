__author__ = 'baohua'

from cmd import Cmd
from select import poll, POLLIN
from subprocess import call,Popen,PIPE
import sys

from easyovs.bridge import brAddFlow,brDelFlow,brDump,brIsExisted,brList,brShow
from flow import Flow
from easyovs.log import info, output, error
from easyovs.util import colorStr


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
        output("***\n Welcome to EasyOVS, type help to see available commands.\n***\n")
        info( '*** Starting CLI:\n' )
        while True:
            try:
                #if self.isatty():
                    #quietRun( 'stty sane' )
                self.cmdloop()
                break
            except KeyboardInterrupt:
                info( '\nInterrupt\n' )

    def do_addflow(self,arg):
        '''
        [bridge] addflow flow
        Add a flow to a bridge.
        '''
        args = arg.replace('"','').replace("'","")
        if 'actions=' not in args:
            output('The flow is not valid.\n')
            return
        i = args.index('actions=')
        actions = args[i:].split()
        args = args[:i].split()
        if len(args)>=2:
            bridge,rule = args[0], args[1:]
        elif self.bridge:
            bridge,rule = self.bridge, args
        else:
            output("Please use [bridge] addflow flow.\n")
        if not rule or not actions or len(actions)!=1:
            output('The flow is not valid.\n')
            return
        rule = ','.join(rule)
        actions = ','.join(actions)
        flow = rule + ' ' + actions
        if not brAddFlow(bridge,flow):
            output('Add flow %s to %s failed.\n' %(bridge,flow))
        else:
            output('Add flow %s to %s done.\n' %(bridge,flow))

    def do_delflow(self,arg):
        '''
        [bridge] delflow flow_id
        Del a flow from a bridge.
        '''
        args = arg.split()
        if len(args)>=2:
            flow_ids = ' '.join(args[1:]).replace(',',' ').split()
            if not brDelFlow(args[0],flow_ids):
                output('Del flow#%s from %s failed.\n' %(' '.join(flow_ids),args[0]))
            else:
                output('Del flow#%s from %s done.\n' %(' '.join(flow_ids),args[0]))
        elif len(args)==1 and self.bridge:
            if not brDelFlow(self.bridge,arg):
                output('Del flow#%s from %s failed.\n' %(arg,self.bridge))
            else:
                output('Del flow#%s from %s done.\n' %(arg,self.bridge))
        else:
            output("Please use [bridge] delflow flow_id.\n")

    def do_dump(self,arg):
        '''
        [bridge] dump
        Dump the flows from a bridge.
        '''
        if arg:
            brDump(arg)
        elif self.bridge:
            brDump(self.bridge)
        else:
            output("Please give a valid bridge.\n")
            return

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
            output('Current default bridge is %s\n' %self.bridge)
        else:
            output('Default bridge is not set yet.\nPlease try <bridge> set.\n')

    def do_help( self, line ):
        "Describe available CLI commands."
        Cmd.do_help( self, line )
        if line is '':
            output( self.helpStr )

    def do_list(self,_arg):
        '''
        List available bridges in the system
        '''
        brList()

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
            output('Set the default bridge to %s.\n' %self.bridge)

    def do_sh( self, line ):
        "Run an external shell command"
        call( line, shell=True )

    def do_show(self,arg):
        '''
        Show port details of a bridge, with neutron information.
        '''
        if arg:
            br = arg
            brShow(arg)
        elif self.bridge:
            brShow(self.bridge)
        else:
            output("Please give a valid bridge.\n")
            return

    def emptyline( self ):
        "Don't repeat last command when you hit return."
        pass

    def default(self,line):
        #bridge, cmd, line = self.parseline( line )
        if len(line.split()) < 2:
            error( '*** Unknown command: %s ***\n' % line )
            return
        bridge,cmd,args='','',''
        if len(line.split()) == 2:
            bridge,cmd = line.split()
        else:
            bridge,cmd,args = line.split()[0],line.split()[1],' '.join(line.split()[2:])
        if brIsExisted(bridge):
            try:
                if args:
                    getattr(self,'do_%s' %(cmd))(' '.join([bridge,args]))
                else:
                    getattr(self,'do_%s' %(cmd))(bridge)
            except AttributeError:
                error( '*** Unknown command: %s, cmd=%s, bridge=%s, args=%s ***\n' % (line,cmd,bridge,args) )
        else:
            error( '*** Bridge %s is not existed\n' %bridge )