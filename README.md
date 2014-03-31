easyOVS
=======

Provide easier and powerful operation on OpenvSwitch.

version 0.1

#What is easyOVS
easyOVS provides more convinient and fluent way to operation your OpenvSwitch bridges, such as list them, dump their flows and add/del some flows.
Just run:

`sudo easyovs`

easyOVS will show an interactive CLI, which supports command suggestions and beautiful output.
  
#Documentation

##Commands
###delflow  
`[bridge|default] delflow id`

###dump
`[bridge|default] dump`, the default output would look like

```
EasyOVS> s1 dump
ID TAB PKT       PRI   MATCH                                                       ACT                 
0  0   0         2400  dl_dst=ff:ff:ff:ff:ff:ff                                    CONTROLLER:65535    
1  0   0         2400  arp                                                         CONTROLLER:65535    
2  0   0         2400  dl_type=0x88cc                                              CONTROLLER:65535    
3  0   0         2400  ip,nw_proto=2                                               CONTROLLER:65535    
4  0   0         801   ip                                                          CONTROLLER:65535    
5  0   2         800                
```

###exit|quit
Input `exit` or `quit` to exit it.

###help
Will show the available commands and some usage examples.

###list  
List the available bridges. The output would look like
```
 EasyOVS> list
s1
 Port:		s1-eth2 s1 s1-eth1
 Interface:	s1-eth2 s1 s1-eth1
 Controller:	ptcp:6634 tcp:127.0.0.1:6633
 Fail_Mode:	secure
s2
 Port:		s2 s2-eth3 s2-eth2 s2-eth1
 Interface:	s2 s2-eth3 s2-eth2 s2-eth1
 Controller:	tcp:127.0.0.1:6633 ptcp:6635
 Fail_Mode:	secure
s3
 Port:		s3-eth1 s3-eth3 s3-eth2 s3
 Interface:	s3-eth1 s3-eth3 s3-eth2 s3
 Controller:	ptcp:6636 tcp:127.0.0.1:6633
 Fail_Mode:	secure

``` 

###set  
`[bridge set]`
Set the default bridge.

###show
Show the current default bridge.

#Features

#Installation

#Credits