__author__ = 'baohua'

from subprocess import call,Popen,PIPE
import subprocess
import sys

import termios
from flow import Flow
from easyovs.log import output,debug
from easyovs.util import fetchFollowingNum,fetchValueBefore,fetchValueBetween
from neutron import  get_neutron_ports

def checkBr(func):
    def wrapper(self,*arg):
        if not self.isExisted():
            output('The bridge does not exist.\n You can check available bridges using list\n')
            return None
        else:
            return func(self,*arg)
    return wrapper

class Bridge(object):
    """
    An OpenvSwitch bridge, typically is a datapath, e.g., br-int
    """
    def __init__( self, bridge):
        self.bridge = bridge
        self.flows = []
        self.flows_db= '/tmp/tmp_%s_flows' %self.bridge

    def isExisted(self):
        if not self.bridge:
            return False
        cmd="ovs-vsctl show|grep -q %s" %self.bridge
        return call(cmd,shell=True) == 0

    @checkBr
    def addFlow(self, flow):
        """
        Return True or False to add a flow.
        """
        if not flow:
            return False
        addflow_cmd='ovs-ofctl add-flow %s "%s"' %(self.bridge,flow)
        result = Popen(addflow_cmd,stdout=subprocess.PIPE,shell=True).stdout.read()
        return True

    @checkBr
    def delFlow(self,ids):
        """
        Return True or False to del a flow from given list.
        """
        if len(ids) <= 0:
            return False
        if not self.flows:
            self.updateFlows()
        del_flows=[]
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        for id in ids:
            if type(id) == str and id.isdigit():
                id = int(id)
            else:
                continue
            if id >= len(self.flows):
                continue
            else:
                del_flow = self.flows[id]
                del_flow.fmtOutput()
                output('Del the flow? [Y/n]: ')
                new = termios.tcgetattr(fd)
                new[3] = new[3] & ~termios.ICANON
                try:
                   termios.tcsetattr(fd, termios.TCSADRAIN, new)
                   while True:
                       input = sys.stdin.read(1)
                       if input == 'n' or input == 'N':
                           output('\tCancel the deletion.\n')
                           break
                       elif input == 'y' or input == 'Y' or input != '\n':
                           del_flows.append(del_flow)
                           output('\n')
                           break
                       else:
                           output('\nWrong, please input [Y/n]: ')
                           continue
                finally:
                   termios.tcsetattr(fd, termios.TCSADRAIN, old)
        self.updateFlows(True)
        flows_db_new = self.flows_db+'.new'
        f = open(self.flows_db,'r')
        f_new = open(flows_db_new,'w')
        while True:
            lines = f.readlines(1000)
            if not lines:
                break
            for line in lines:
                flow = self.extractFlow(line)
                if flow not in del_flows:
                    f_new.write('%s' %line)
                else:
                    debug("Del the flow:\n")
                    #del_flow.fmtOutput()
        f.close()
        f_new.close()
        replace_cmd="ovs-ofctl replace-flows %s %s" %(self.bridge,flows_db_new)
        result = Popen(replace_cmd,stdout=subprocess.PIPE,shell=True).stdout.read()
        self.updateFlows()
        return True

    @checkBr
    def updateFlows(self,db=False):
        """
        Update the OpenvSwitch table rules into self.flows, and also to db if enabled.
        """
        cmd="ovs-ofctl dump-flows %s" %self.bridge
        id,flows = 0, []
        if db:
            f = open(self.flows_db,'w')
        result= Popen(cmd, stdout=subprocess.PIPE,shell=True).stdout.read()
        for l in result.split('\n'):
            l=l.strip()
            if l.startswith('cookie='):
                flow = self.extractFlow(l)
                if flow:
                    flows.append(flow)
                    if db:
                        f.write('%s\n' %l)
        if db:
            f.close()
        flows = sorted(flows, reverse=True)
        for flow in flows:
            flow.id = id
            id += 1
        self.flows = flows
        debug('updateFlows:len flows=%u\n' %len(self.flows))

    @checkBr
    def getFlows(self):
        """
        Return a dict of flows in the bridge.
        """
        self.updateFlows()
        if len(self.flows)>0:
            return self.flows
        else:
            return {}

    def extractFlow(self,line):
        """
        Return a Flow or None, converted from a line of original output
        """
        line = line.strip()
        table,packet,priority,match,actions ='','','','',''
        if line.startswith('cookie='):
            table = fetchFollowingNum(line,'table=')
            packet = fetchFollowingNum(line,'n_packets=')
            if table == None or packet == None:
                return None
            for field in line.split():
                if field.startswith('priority='):
                    priority = fetchFollowingNum(field,'priority=')
                    if priority == None:
                        return None
                    match = field.replace('priority=%u' %priority,'').lstrip(',')
                    if not match:
                        match = r'*'
                elif field.startswith('actions='):
                    actions=field.replace('actions=','').rstrip('\n')
            if priority == '': #There is no priority= field
                match = line.split()[len(line.split())-2]
            return Flow(self.bridge,table,packet,priority,match,actions)
        else:
            return None

    @checkBr
    def getPorts(self):
        """
        Return a dict of the ports (port, addr, tag, type) on the bridge, looks like
        {
            'qvoxxx':{
                'port':2,
                'addr':08:91:ff:ff:f3,
                'tag':1,
                'type':internal,
            }
        }
        """
        result={}
        cmd="ovs-ofctl show %s" %self.bridge
        try:
            cmd_output= Popen(cmd, stdout=subprocess.PIPE,shell=True).stdout.read()
        except Exception:
            return {}
        #output('%-8s%-16s%-16s\n' %('PORT','INTF','ADDR'))
        br_list = getBridges()
        for l in cmd_output.split('\n'):
            if l.startswith(' ') and l.find('(')>=0 and l.find(')')>=0:
                l=l.strip()
                port = fetchValueBefore(l,'(')
                intf = fetchValueBetween(l,'(',')')
                addr = l[l.find('addr:')+len('addr:'):]
                #output('%-8s%-16s%-16s\n' %(port,intf,addr))
                if self.bridge in br_list:
                    if intf in br_list[self.bridge]['Port']:
                        tag = br_list[self.bridge]['Port'][intf].get('tag','0')
                        type = br_list[self.bridge]['Port'][intf].get('type','0')
                else:
                    tag, type = '0',''
                result[intf] = {'port':port,'addr':addr,'tag':tag,'type':type}
        return result

def brAddFlow(bridge,flow):
    if 'actions=' in flow and len(flow.split())==2:
        return Bridge(bridge).addFlow(flow)
    else:
        return False

def brDelFlow(bridge,ids):
    debug('brDelFlow: %s: %s\n' %(bridge,','.join(ids)))
    if type(ids) == str and ids.isdigit():
        return Bridge(bridge).delFlow([ids])
    else:
        return Bridge(bridge).delFlow(ids)

def brGetFlows(bridge):
    try:
        return Bridge(bridge).getFlows()
    except Exception:
        return None

def brIsExisted(bridge):
    """
    Return True of False of a bridge's existence.
    """
    try:
        return Bridge(bridge).isExisted()
    except Exception:
        return False

def brGetPorts(bridge):
    """
    Return a dict of all available bridges, looks like
    """
    try:
        return Bridge(bridge).getPorts()
    except Exception:
        return {}

def brList():
    """
    List available bridges.
    """
    bridges = getBridges()
    if not bridges:
        output('None bridge exists.\n')
        return
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

def brDump(bridge):
    """
    Dump the port information of a given bridges.
    """
    flows=brGetFlows(bridge)
    debug('brDump: len flows=%u\n' %len(flows))
    if flows:
        Flow.bannerOutput()
        for f in flows:
            f.fmtOutput()

def brShow(bridge):
    """
    Show information of a given bridges.
    """
    ovs_ports = brGetPorts(bridge)
    if not ovs_ports:
        output('No port is found at bridge %s\n' %bridge)
        return
    neutron_ports = get_neutron_ports()
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

def getBridges():
    """
    Return a dict of all available bridges, looks like
    {
        'br-int':{
            'Controller':[],
            'fail_mode':'',
            'Port':{
             'qvoxxx': {
                'tag':'1', //tagid
                'type':'internal', //tagid
                }
        },
    }
    """
    bridges,br={},''
    cmd='ovs-vsctl show'
    try:
        result= Popen(cmd, stdout=PIPE,shell=True).stdout.read()
    except Exception:
        return {}
    for l in result.split('\n'):
        l=l.strip().replace('"','')
        if l.startswith('Bridge '):
            br = l.lstrip('Bridge ')
            bridges[br]={}
            bridges[br]['Controller']=[]
            bridges[br]['Port']={}
            bridges[br]['fail_mode'] = ''
        else:
            if l.startswith('Controller '):
                bridges[br]['Controller'].append(l.replace('Controller ',''))
            elif l.startswith('fail_mode: '):
                bridges[br]['fail_mode']=l.replace('fail_mode: ','')
            elif l.startswith('Port '):
                phy_port = l.replace('Port ','') #e.g., br-eth0
                bridges[br]['Port'][phy_port]={'tag':0,'type':''}
            elif l.startswith('tag: '):
                bridges[br]['Port'][phy_port]['tag'] = l.replace('tag: ','')
            elif l.startswith('Interface '):
                intf = l.replace('Interface ','')
            elif l.startswith('type: '):
                bridges[br]['Port'][phy_port]['type'] = l.replace('type: ','')
    return bridges
