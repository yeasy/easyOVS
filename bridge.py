__author__ = 'baohua'

from subprocess import call,Popen
import subprocess
import sys

import termios
from flow import Flow
from log import output
from util import fetchFieldNum


class Bridge(object):
    """
    An OpenvSwitch bridge, typically is a datapath, e.g., br-int
    """
    def __init__( self, bridge):
        self.bridge = bridge
        self.flows = []
        self.flows_db= '/tmp/tmp_%s_flows' %self.bridge

    def isExisted(self):
        cmd="ovs-vsctl show|grep -q %s" %self.bridge
        return call(cmd,shell=True) == 0

    def delFlow(self,id):
        if not self.flows:
            self.updateFlows()
        if id < 0 or id >= len(self.flows):
            return False
        del_flow = self.flows[id]
        del_flow.fmtOutput()
        output("Del the flow? Y/n ")
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        new = termios.tcgetattr(fd)
        new[3] = new[3] & ~termios.ICANON
        try:
           termios.tcsetattr(fd, termios.TCSADRAIN, new)
           while True:
               input = sys.stdin.read(1)
               if input == 'n' or input == 'N':
                   output('Canceled.\n')
                   return False
               elif input == 'y' or input == 'Y' or input != '\n':
                   output('\n')
                   break
               else:
                   output('\nWrong, please input [Y/n] ')
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
                output(flow)
                if flow != del_flow:
                    f_new.write('%s' %line)
        f.close()
        f_new.close()
        replace_cmd="ovs-ofctl replace-flows %s %s" %(self.bridge,flows_db_new)
        result = Popen(replace_cmd,stdout=subprocess.PIPE,shell=True).stdout.read()

    def updateFlows(self,to_file=False):
        """
        Update the self.flows variables with the OpenvSwitch Content.
        """
        cmd="ovs-ofctl dump-flows %s" %self.bridge
        id,flows = 0, []
        if to_file:
            f = open(self.flows_db,'w')
        result= Popen(cmd, stdout=subprocess.PIPE,shell=True).stdout.read()
        for l in result.split('\n'):
            l=l.strip()
            if l.startswith('cookie='):
                flow = self.extractFlow(l)
                if flow:
                    flows.append(flow)
                    if to_file:
                        f.write('%s\n' %l)
        if to_file:
            f.close()
        #flows=sorted(flows,key=lambda flow: flow.priority,reverse=True)
        #flows=sorted(flows,key=lambda flow: flow.table)
        flows = sorted(flows, reverse=True)
        for flow in flows:
            flow.id = id
            id += 1
        self.flows = flows

    def dumpFlows(self):
        self.updateFlows()
        Flow.bannerOutput()
        for f in self.flows:
            f.fmtOutput()

    def extractFlow(self,line):
        """
        Return a Flow or None, converted from a line of original output
        """
        line = line.strip()
        match,actions = '',''
        if line.startswith('cookie='):
            table = fetchFieldNum(line,'table=')
            packet = fetchFieldNum(line,'n_packets=')
            if table == None or packet == None:
                return None
            for fields in line.split():
                if fields.startswith('priority='):
                    priority = fetchFieldNum(fields,'priority=')
                    if priority == None:
                        return None
                    match = fields.replace('priority=%u' %priority,'').lstrip(',')
                elif fields.startswith('actions='):
                    actions=fields.replace('actions=','').rstrip('\n')
            return Flow(self.bridge,table,packet,priority,match,actions)
        else:
            return None

    def monitor(self):
        pass

def brIsExisted(bridge):
    return Bridge(bridge).isExisted()

def brDelFlow(bridge,id):
    return Bridge(bridge).delFlow(id)

def brDumpFlows(bridge):
    return Bridge(bridge).dumpFlows()

def brMon(bridge):
    return Bridge(bridge).dumpFlows()

def brList():
    bridges={}
    br=''
    cmd='ovs-vsctl show'
    result= Popen(cmd, stdout=subprocess.PIPE,shell=True).stdout.read()
    for l in result.split('\n'):
        l=l.strip().replace('"','')
        if l.startswith('Bridge '):
            br = l.lstrip('Bridge ')
            bridges[br]={}
            bridges[br]['Controller']=[]
            bridges[br]['Port']=[]
            bridges[br]['Interface']=[]
            bridges[br]['fail_mode'] = ''
        else:
            if l.startswith('Controller '):
                bridges[br]['Controller'].append(l.replace('Controller ',''))
            elif l.startswith('fail_mode: '):
                bridges[br]['fail_mode']=l.replace('fail_mode: ','')
            elif l.startswith('Port '):
                bridges[br]['Port'].append(l.replace('Port ',''))
            elif l.startswith('Interface '):
                bridges[br]['Interface'].append(l.replace('Interface ',''))
    br_info = ''
    br_list = bridges.keys()
    for br in sorted(br_list):
        br_info = "%s\n"  %(br)
        if bridges[br]['Port']:
            br_info += " Port:\t\t%s\n"  %(' '.join(bridges[br]['Port']))
        if bridges[br]['Interface']:
            br_info += " Interface:\t%s\n" %(' '.join(bridges[br]['Interface']))
        if bridges[br]['Controller']:
            br_info += " Controller:\t%s\n"  %(' '.join(bridges[br]['Controller']))
        if bridges[br]['fail_mode']:
            br_info += " Fail_Mode:\t%s\n"  %(bridges[br]['fail_mode'])
    return br_info
