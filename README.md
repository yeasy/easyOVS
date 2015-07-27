easyOVS [![Build Status](https://travis-ci.org/yeasy/easyOVS.svg?style=flat-square)](https://travis-ci.org/yeasy/easyOVS)
===

Provide smarter and powerful operation on OpenvSwitch bridges in OpenStack.

version 0.4

# What is easyOVS
easyOVS provides a more convenient and fluent way to operate your 
[OpenvSwitch](http://openvswitch.org) bridges in OpenStack platform,
such as list their ports, dump their flows and add/del some flows in a smart 
style with color!

If using in OpenStack environment (Currently tested from the Havana to the Juno 
release), easyOVS will associate the ports with the vm MAC/IP and VLAN Tag information, and the iptables rules for vm.

# Installation and Usage

## Install on host
Download the latest version and install.

`git clone https://github.com/yeasy/easyOVS.git && sudo bash ./easyOVS/util/install.sh`

After the installation, start easyovs with

`sudo easyovs`

easyOVS will show an interactive CLI, which supports command suggestions and formatted colorful output.

## Run with Docker (recommended)
### No OpenStack Support
```sh
docker run -it \
 --net='host' \
 --privileged \
 -v /var/run/openvswitch/:/var/run/openvswitch/:ro \
  yeasy/easyovs:latest
```

### Enable Openstack support
Replace the following openstack credentials with your own.

```sh
docker run -it \
 --net='host' \
 --privileged \
 -v /var/run/openvswitch/:/var/run/openvswitch/:ro \
 -e OS_USERNAME=$OS_USERNAME \
 -e OS_PASSWORD=$OS_PASSWORD \
 -e OS_TENANT_NAME=$OS_TENANT_NAME \
 -e OS_AUTH_URL=$OS_AUTH_URL \
  yeasy/easyovs:latest
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
EasyOVS> dump s1
ID TAB PKT       PRI   MATCH                                                       ACT
0  0   0         2400  dl_dst=ff:ff:ff:ff:ff:ff                                    CONTROLLER:65535
1  0   0         2400  arp                                                         CONTROLLER:65535
2  0   0         2400  dl_type=0x88cc                                              CONTROLLER:65535
3  0   0         2400  ip,nw_proto=2                                               CONTROLLER:65535
4  0   0         801   ip                                                          CONTROLLER:65535
5  0   2         800
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
-rw-r--r--. 1 root root 2214 Apr  1 14:53 INSTALL
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

# Features
* Support OpenvSwitch version 1.4.6 ~ 2.0.0.
* Support most popular Linux distributions, e.g., Ubuntu,Debian, CentOS and Fedora.
* Format the output to make it clear and easy to compare.
* Show the OpenStack information with the bridge port (In OpenStack environment).
* Delete a flow with its id.
* Show formatted iptables rules with given vm IPs.
* Smart command completion, try tab everywhere.
* Support colorful output.
* Support run local system commands.
* Support run individual command with `-m 'cmd'`

#Credits
Thanks to the [OpenvSwitch](http://openvswitch.org) Team, [Mininet](http://mininet.org) Team and [OpenStack](http://openstack.org) Team, who gives helpful implementation example and useful tools.
