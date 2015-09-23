easyOVS [![Build Status](https://travis-ci.org/yeasy/easyOVS.svg?style=flat-square)](https://travis-ci.org/yeasy/easyOVS)
===

Provide insightful check and operations for OpenStack Neutron!

version 0.5

# What is easyOVS
easyOVS provides a more convenient and fluent way to operate your 
[OpenvSwitch](http://openvswitch.org) bridges, iptables in OpenStack platform,
such as list the rules or validate the configurations in a smart
style with color!

If using in OpenStack environment (Currently tested from the Havana to the Kilo
release), easyOVS will automatically associate the virtual ports with the vm
MAC/IP, VLAN Tag and namespace information, and the iptables rules for vm.

# Features
* Support OpenvSwitch version 1.4.6 ~ 2.1.0.
* Support most popular Linux distributions, e.g., Ubuntu,Debian, CentOS and Fedora.
* Format the output and use color to make it clear and easy to compare.
* Associate the OpenStack information (e.g., vm ip) on the virtual port or rule
* Query openvswitch,iptables,namespace information in smart way.
* Check if the DVR configuration is correct.
* Smart command completion, try tab everywhere.
* Support runing local system commands.
* Support runing individual command with `-m 'cmd'` and quit.

# Installation and Usage

## Install on host
Download the latest version and install.

`git clone https://github.com/yeasy/easyOVS.git && sudo bash ./easyOVS/util/install.sh`

After the installation, start easyovs with

`sudo easyovs`

easyOVS will show an interactive CLI, which supports command suggestions and formatted colorful output.

## Run with Docker (recommended)
remove the ``:ro`` flag if you want to modify the ovs rules or net namespaces.

### No OpenStack Support
```sh
docker run -it \
 --rm \
 --net='host' \
 --pid='host' \
 --privileged \
 -v /var/run/openvswitch/:/var/run/openvswitch/:ro \
 -v /var/run/netns/:/var/run/netns/:ro \
 -v /var/lib/neutron/:/var/lib/neutron/:ro \
 -v /etc/sysctl.conf:/etc/sysctl.conf:ro \
 -v /etc/neutron/:/etc/neutron/:ro \
  yeasy/easyovs:latest
```

### Enable Openstack support
Replace the following openstack credentials with your own.

```sh
docker run -it \
 --rm \
 --net='host' \
 --pid='host' \
 --privileged \
 -v /var/run/openvswitch/:/var/run/openvswitch/:ro \
 -v /var/run/netns/:/var/run/netns/:ro \
 -v /var/lib/neutron/:/var/lib/neutron/:ro \
 -v /etc/sysctl.conf:/etc/sysctl.conf:ro \
 -v /etc/neutron/:/etc/neutron/:ro \
 -e OS_USERNAME=$OS_USERNAME \
 -e OS_PASSWORD=$OS_PASSWORD \
 -e OS_TENANT_NAME=$OS_TENANT_NAME \
 -e OS_AUTH_URL=$OS_AUTH_URL \
  yeasy/easyovs:latest
```

### Wrap with script
Certainly, you can wrap the above command into a script, to run command
directly with Docker container without such long typing, e.g., make a `
./docker-easyovs.sh` file with content as
```sh
#!/bin/sh

export OS_USERNAME=admin
export OS_PASSWORD=admin
export OS_TENANT_NAME=admin
export OS_AUTH_URL=http://127.0.0.1:5000/v2.0

docker run -it \
 --rm \
 --net='host' \
 --pid='host' \
 --privileged \
 -v /var/run/openvswitch/:/var/run/openvswitch/:ro \
 -v /var/run/netns/:/var/run/netns/:ro \
 -v /var/lib/neutron/:/var/lib/neutron/:ro \
 -v /etc/sysctl.conf:/etc/sysctl.conf:ro \
 -v /etc/neutron/:/etc/neutron/:ro \
 -e OS_USERNAME=$OS_USERNAME \
 -e OS_PASSWORD=$OS_PASSWORD \
 -e OS_TENANT_NAME=$OS_TENANT_NAME \
 -e OS_AUTH_URL=$OS_AUTH_URL \
  yeasy/easyovs:latest "$@"
```

Make the script executable and run it.

```sh
# chmod a+x docker-easyovs.sh
# ./docker-easyovs.sh
```

You can also run easyovs command directly with `-m` as
```sh
# ./docker-easyovs.sh -m "dump br-int"
ID TAB PKT       PRI   MATCH                                              ACT
0  0   3525622   2     in_port=int-br-ex                                  drop
1  0   925       1     *                                                  NORMAL
2  23  0         0     *                                                  drop

```

## Upgrade or Delete
If you wanna upgrade easyOVS from a previous version, just run

`sudo bash ./easyOVS/util/install.sh -u`

If you wanna remove the package from the system

`sudo bash ./easyOVS/util/install.sh -d`

## Enable OpenStack Feature
To integrate the port information collected from OpenStack, 
please set the authentication information in your environment: e.g.,
```sh
export OS_USERNAME=demo
export OS_TENANT_NAME=demo
export OS_PASSWORD=admin
export OS_AUTH_URL=http://127.0.0.1:5000/v2.0/
```
Otherwise, set the information into the `etc/easyovs.conf` file.
```sh
[OS]
auth_url = http://127.0.0.1:5000/v2.0
username = demo
password = admin
tenant_name = demo
```

# Documentation

## CLI Commands

### help
Show the available commands and some usage examples.

### list
List the available bridges. The output would look like
```sh
 EasyOVS> list
s1
 Port:		s1-eth2 s1 s1-eth1
 Interface:	s1-eth2 s1 s1-eth1
 Controller:ptcp:6634 tcp:127.0.0.1:6633
 Fail_Mode:	secure
s2
 Port:		s2 s2-eth3 s2-eth2 s2-eth1
 Interface:	s2 s2-eth3 s2-eth2 s2-eth1
 Controller:tcp:127.0.0.1:6633 ptcp:6635
 Fail_Mode:	secure
s3
 Port:		s3-eth1 s3-eth3 s3-eth2 s3
 Interface:	s3-eth1 s3-eth3 s3-eth2 s3
 Controller:ptcp:6636 tcp:127.0.0.1:6633
 Fail_Mode:	secure
```

### show
`EasyOVS> show [bridge|default]`

Show the ports information of a given bridge. The output would look like
```sh
 EasyOVS> show br-int
br-int
Intf                Port        Vlan    Type        vmIP            vmMAC
int-br-eth0         15
qvo260209fa-72      11          1                   192.168.0.4     fa:16:3e:0f:17:04       
qvo583c7038-d3      2           1                   192.168.0.2     fa:16:3e:9c:dc:3a       
qvo8bf9cba2-3f      9           1                   192.168.0.5     fa:16:3e:a2:2f:0e
qvod4de9fe0-6d      8           2                   10.0.0.2        fa:16:3e:38:2b:2e       
br-int              LOCAL               internal
```
### addbr
`EasyOVS> addbr br-test`

Create a new bridge. The output would look like

```sh
EasyOVS> addbr br1,br2
bridge br1 was created
bridge br2 was created
```

### delbr
`EasyOVS> delbr br-test`

Delete a bridge. The output would look like

```sh
EasyOVS> delbr br1
bridge br1 was deleted
```

### dump
`EasyOVS> dump [bridge|default]`

Dump flows in a bridge. The output would look like

```sh
EasyOVS> dump br-tun
ID PKT       TAB PRI   MATCH                                                       ACT
0  44        0   1     in_port=gre-ac1da15d                                        resubmit(,3)
1  1         0   1     in_port=gre-ac1da15f                                        resubmit(,3)
2  40        0   1     in_port=patch-int                                           resubmit(,2)
3  0         0   1     in_port=vxlan-ac1da15d                                      resubmit(,4)
4  0         0   1     in_port=vxlan-ac1da15f                                      resubmit(,4)
5  0         0   0     *                                                           drop
6  40        2   0     dl_dst=00::00/01:00::00                                     resubmit(,20)
7  0         2   0     dl_dst=01:00::00/01:00::00                                  resubmit(,22)
8  44        3   1     tun_id=0x2                                                  mod_vlan_vid:1,resubmit(,10)
9  1         3   0     *                                                           drop
10 0         4   0     *                                                           drop
11 44        10  1     *                                                           learn(table=20,hard_timeout=300,priority=1,NXM_OF_VLAN_TCI[0..11],NXM_OF_ETH_DST[]=NXM_OF_ETH_SRC[],load:0->NXM_OF_VLAN_TCI[],load:NXM_NX_TUN_ID[]->NXM_NX_TUN_ID[],output:NXM_OF_IN_PORT[]),output:patch-int
12 3         20  0     *                                                           resubmit(,22)
13 3         22  0                                                                 strip_vlan,set_tunnel:0x2,output:gre-ac1da15f,output:gre-ac1da15d
14 0         22  0     *                                                           drop
```

### addflow
`EasyOVS> addflow [bridge|default] [match] actions=[action]`

Add a flow into the bridge, e.g.,

`EasyOVS> addflow br-int priority=3 ip actions=OUTPUT:1`

### delflow
`EasyOVS> delflow [bridge|default] id1 id2...`

Delete flows with given ids (see the first column of the `dump` output).


### set
`EasyOVS> set bridge`

Set the default bridge. Then you will go into a bridge mode, and can ignore the bridge parameter when using the
command.
```sh
EasyOVS> set br-int
Set the default bridge to br-int.
EasyOVS: br-int> 
```

### exit
`EasyOVS> exit`

Exit from the bridge mode, or quit EasyOVS if already at the top level.

### get
`EasyOVS> get`

Get the current default bridge.
```sh
EasyOVS: br-int> get
Current default bridge is br-int
```

### ipt
`EasyOVS> ipt vm vm_ip...`

Show the related iptables rules of the given vms.
```sh
EasyOVS> ipt vm 192.168.0.2
## IP = 192.168.0.2, port = qvo583c7038-d ##
    PKTS	SOURCE          DESTINATION     PROT  OTHER               
#IN:
     672	all             all             all   state RELATED,ESTABLISHED
       0	all             all             tcp   tcp dpt:22          
       0	all             all             icmp                      
       0	192.168.0.4     all             all                       
       3	192.168.0.5     all             all                       
       8	10.0.0.2        all             all                       
   85784	192.168.0.3     all             udp   udp spt:67 dpt:68   
#OUT:
    196K	all             all             udp   udp spt:68 dpt:67   
   86155	all             all             all   state RELATED,ESTABLISHED
    1241	all             all             all                       
#SRC_FILTER:
   59163	192.168.0.2     all             all   MAC FA:16:3E:9C:DC:3A
```
`EasyOVS> ipt show [table] [chain]...`

Show the related iptables rules of the given table or chain.
```sh
EasyOVS> ipt show filter FORWARD
table=filter
chain=FORWARD
1 0 0 ACCEPT all -- * virbr0 0.0.0.0/0 192.168.122.0/24 ctstate RELATED,ESTABLISHED
2 0 0 ACCEPT all -- virbr0 * 192.168.122.0/24 0.0.0.0/0
3 0 0 ACCEPT all -- virbr0 virbr0 0.0.0.0/0 0.0.0.0/0
4 0 0 REJECT all -- * virbr0 0.0.0.0/0 0.0.0.0/0 reject-with icmp-port-unreachable
5 0 0 REJECT all -- virbr0 * 0.0.0.0/0 0.0.0.0/0 reject-with icmp-port-unreachable
6 691K 1117M DOCKER all -- * docker0 0.0.0.0/0 0.0.0.0/0
7 691K 1117M ACCEPT all -- * docker0 0.0.0.0/0 0.0.0.0/0 ctstate RELATED,ESTABLISHED
8 463K 26M ACCEPT all -- docker0 !docker0 0.0.0.0/0 0.0.0.0/0
9 0 0 ACCEPT all -- docker0 docker0 0.0.0.0/0 0.0.0.0/0
```

### ns
Check namespaces related operations
`EasyOVS> ns list` will list all existing namespace names.
`EasyOVS> ns show id_prefix` will show the information of namespace whose id has the prefix.
`EasyOVS> ns find pattern` will find the namespace whose content has the pattern.

```sh
EasyOVS> ns show id
# Namespace = id
ID    Intf              Mac                 IPs
12    tapd41cd120-62    fa:16:3e:75:01:0e   11.3.3.2/24, 169.254.169.254/16
```

### query

`EasyOVS> query vm_ip1, port_id...`

Show the related port information by giving the IP address or part of the 
id string.

```sh
EasyOVS> query 10.0.0.2,c4493802
## port_id = f47c62b0-dbd2-4faa-9cdd-8abc886ce08f
status: ACTIVE
name:
allowed_address_pairs: []
admin_state_up: True
network_id: ea3928dc-b1fd-4a1a-940e-82b8c55214e6
tenant_id: 3a55e7b5f5504649a2dfde7147383d02
extra_dhcp_opts: []
binding:vnic_type: normal
device_owner: compute:az_compute
mac_address: fa:16:3e:52:7a:f2
fixed_ips: [{u'subnet_id': u'94bf94c0-6568-4520-aee3-d12b5e472128', u'ip_address': u'10.0.0.2'}]
id: f47c62b0-dbd2-4faa-9cdd-8abc886ce08f
security_groups: [u'7c2b801b-4590-4a1f-9837-1cceb7f6d1d0']
device_id: c3522974-8a08-481c-87b5-fe3822f5c89c
## port_id = c4493802-4344-42bd-87a6-1b783f88609a
status: ACTIVE
name:
allowed_address_pairs: []
admin_state_up: True
network_id: ea3928dc-b1fd-4a1a-940e-82b8c55214e6
tenant_id: 3a55e7b5f5504649a2dfde7147383d02
extra_dhcp_opts: []
binding:vnic_type: normal
device_owner: compute:az_compute
mac_address: fa:16:3e:94:84:90
fixed_ips: [{u'subnet_id': u'94bf94c0-6568-4520-aee3-d12b5e472128', u'ip_address': u'10.0.0.4'}]
id: c4493802-4344-42bd-87a6-1b783f88609a
security_groups: [u'7c2b801b-4590-4a1f-9837-1cceb7f6d1d0']
device_id: 9365c842-9228-44a6-88ad-33d7389cda5f
```

### dvr
*This feature is still experimental.*
Check your local dvr configuration information, such as the virtual ports,
namespaces, iptables, etc.

`EasyOVS> dvr check [compute, net]` will check for the given node.

If no node type is given, it will smartly guess on what node.

```sh
# No type given, guessing...compute node
=== Checking DVR on compute node ===
>>> Checking config files...
# Checking file = /etc/sysctl.conf...
# Checking file = /etc/neutron/neutron.conf...
# Checking file = /etc/neutron/plugins/ml2/ml2_conf.ini...
file /etc/neutron/plugins/ml2/ml2_conf.ini Not has [agent]
file /etc/neutron/plugins/ml2/ml2_conf.ini Not has l2_population = True
file /etc/neutron/plugins/ml2/ml2_conf.ini Not has enable_distributed_routing = True
file /etc/neutron/plugins/ml2/ml2_conf.ini Not has arp_responder = True
# Checking file = /etc/neutron/l3_agent.ini...
<<< Checking config files has warnings

>>> Checking bridges...
# Existing bridges are br-tun, br-int, br-eno1, br-ex
# Vlan bridge is at br-tun, br-int, br-eno1, br-ex
<<< Checking bridges passed

>>> Checking vports ...
## Checking router port = qr-b0142af2-12
### Checking rfp port rfp-f046c591-7
Found associated floating ips : 172.29.161.127/32, 172.29.161.126/32
### Checking associated fpr port fpr-f046c591-7
### Check related fip_ns=fip-9e1c850d-e424-4379-8ebd-278ae995d5c3
Bridging in the same subnet
fg port is attached to br-ex
floating ip 172.29.161.127 match fg subnet
floating ip 172.29.161.126 match fg subnet
Checking chain rule number: neutron-postrouting-bottom...Passed
Checking chain rule number: OUTPUT...Passed
Checking chain rule number: neutron-l3-agent-snat...Passed
Checking chain rules: neutron-postrouting-bottom...Passed
Checking chain rules: PREROUTING...Passed
Checking chain rules: OUTPUT...Passed
Checking chain rules: POSTROUTING...Passed
Checking chain rules: POSTROUTING...Passed
Checking chain rules: neutron-l3-agent-POSTROUTING...Passed
Checking chain rules: neutron-l3-agent-PREROUTING...Passed
Checking chain rules: neutron-l3-agent-OUTPUT...Passed
DNAT for incomping: 172.29.161.127 --> 10.0.0.3 passed
Checking chain rules: neutron-l3-agent-float-snat...Passed
SNAT for outgoing: 10.0.0.3 --> 172.29.161.127 passed
Checking chain rules: neutron-l3-agent-OUTPUT...Passed
DNAT for incomping: 172.29.161.126 --> 10.0.0.216 passed
Checking chain rules: neutron-l3-agent-float-snat...Passed
SNAT for outgoing: 10.0.0.216 --> 172.29.161.126 passed
## Checking router port = qr-8c41bfc7-56
Checking passed already
<<< Checking vports passed
```

### sh
`EasyOVS> sh cmd`

Run the system cmd locally, e.g., using ls -l to show local directory's content.
```sh
EasyOVS> sh ls -l
total 48
drwxr-xr-x. 2 root root 4096 Apr  1 14:34 bin
drwxr-xr-x. 5 root root 4096 Apr  1 14:56 build
drwxr-xr-x. 2 root root 4096 Apr  1 14:56 dist
drwxr-xr-x. 2 root root 4096 Apr  1 14:09 doc
drwxr-xr-x. 4 root root 4096 Apr  1 14:56 easyovs
-rw-r--r--. 1 root root  660 Apr  1 14:56 easyovs.1
drwxr-xr-x. 2 root root 4096 Apr  1 14:56 easyovs.egg-info
-rw-r--r--. 1 root root 2214 Apr  1 14:53 INSTALL.md
-rw-r--r--. 1 root root 1194 Apr  1 14:53 Makefile
-rw-r--r--. 1 root root 3836 Apr  1 14:53 README.md
-rw-r--r--. 1 root root 1177 Apr  1 14:53 setup.py
drwxr-xr-x. 2 root root 4096 Apr  1 14:09 util
```

### quit
Input `^d` or `quit` to exit EasyOVS.

##Options
### -h
Show the help message on supported options, such as
```sh
$ easyovs -h
Usage: easyovs [options]
(type easyovs -h for details)

The easyovs utility creates operation CLI from the command line. It can run
given commands, invoke the EasyOVS CLI, and run tests.

Options:
  -h, --help            show this help message and exit
  -c, --clean           clean and exit
  -m CMD, --cmd=CMD     Run customized commands for tests.
  -v VERBOSITY, --verbosity=VERBOSITY
                        info|warning|critical|error|debug|output
  --version
```

### -c
Clean the env.

### -m
Run the given command in easyovs directly, show the output, and exit.
```sh
easyovs -m "show br-int"
```

E.g. `easyovs -m 'br-int dump'`.

### -v
Set verbosity level.

### --version
Show the version information.

#Known Issues
* Using Docker to run easyOVS, when local host's namespaces are changed during the running. easyOVS may complain access namespace error. This is possiblly due to the access privilege with Docker. Just restart it.
* The DVR check feature can check pure network node or pure compute node, but does not support mixing those two types together at one node (This is not recommended in production environment).

#Credits
Thanks to the [OpenvSwitch](http://openvswitch.org) Team, [Mininet](http://mininet.org) Team and [OpenStack](http://openstack.org) Team, who gives helpful implementation example and useful tools.
