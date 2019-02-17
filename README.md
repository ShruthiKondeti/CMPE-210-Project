# CMPE-210-Project
Implemented a technique to reduce DoS (denial-of-service) attacks by maintaining constant communication bandwidth of the queues using Rest API's in Open virtual switches (OVS) connected to RYU controller. 


In this project we address one serious SDN-specific attack that is a data-to-control plane saturation attack, which overloads the infrastructure of SDN networks.
In this, an attacker produces a large amount of table-miss packet_in messages by flooding the network with UDP packets to consume resources in both control plane and data plane.
Our prototype provides an efficient way to reduce DoS (denial-of-service) attacks by maintaining constant communication bandwidth of the queues in OVS (open virtual switch) using RYU controller.
QoS regulation techniques can be used to reduce the impact of DoS (denial-of-service) attacks on end host. 
This can also be mitigated by dropping the packets when it exceeds a particular threshold obtained by port stats.


**************SYSTEM REQUIREMENT **************************

1] SDN HUB

Process to install SDN HUB :
Visit http://sdnhub.org/tutorials/openflow-1-3/ .
It has everything pre-installed ==> http://sdnhub.org/tutorials/sdn-tutorial-vm/ 
follow the steps given in above link

2] Steps

Once you are done with installation of SDN hub.
Open 3 terminals in sdn hub. 
First is used to create topology using mininet. 
Second terminal is used to set openflow protocol 1.4 
Third terminal we run the python code to start our project.

1st terminal:
In order to create topology using mininet, type the following command
sudo mn --custom Topology.py --topo mytopo --controller=remote,protocols=OpenFlow13


"""Custom topology example
Two directly connected switches plus a host for each switch:
	host --- switch --- switch --- host

Adding the 'topos' dict with a key/value pair to generate our newly defined
topology enables one to pass in '--topo=mytopo' from the command line.
"""
from mininet.topo import Topo
class MyTopo( Topo ):
	"Simple topology example."
	def __init__( self ):
		"Create custom topo."

	# Initialize topology
	Topo.__init__( self )

	# Add hosts and switches
	leftHost = self.addHost( 'h1' )
	rightHost = self.addHost( 'h2' )
	leftHost1 = self.addHost( 'h3' )
	rightHost1 = self.addHost( 'h4' )
	leftSwitch = self.addSwitch( 's1' )
	rightSwitch = self.addSwitch( 's2' )
	
	# Add links
	self.addLink( leftHost, leftSwitch )
	self.addLink( leftHost1, leftSwitch )
	self.addLink( leftSwitch, rightSwitch )
	self.addLink( rightSwitch, rightHost )
	self.addLink( rightSwitch, rightHost1 )

topos = { 'mytopo': ( lambda: MyTopo() ) }


TERMINAL 2 :

Once we are done with creating the topology we now open the secon terminal and type following command to set bridge to open flow 13.

sudo ovs-vsctl set Bridge s1 protocols=OpenFlow13

also in order to set port 6632 as listening port to access OVSDB, we type following command in terminal two itself.

sudo ovs-vsctl set-manager ptcp:6632


TERMINAL 3 :

Copy SW_TM4.py in home/ubuntu/ryu/ryu/app

cd /home/ubuntu/ryu/ && ./bin/ryu-manager --verbose ryu/app/rest_qos.py ryu/app/SW_TM4.py ryu/app/rest_conf_switch.py


Now type pingall in terminal 1 and we get the following output :

** Ping: testing ping reachability
h1 -> h2 h3 h4 
h2 -> h1 h3 h4 
h3 -> h1 h2 h4 
h4 -> h1 h2 h3 
*** Results: 0% dropped (12/12 received)


Output which we get in terminal 3 after pingall :

packet in 2 9e:77:36:b5:b0:11 0a:f3:9e:0d:5e:7d 2
EVENT ofp_event->Switching_hub EventOFPPacketIn
packet in 1 d2:9e:d5:70:60:49 ff:ff:ff:ff:ff:ff 2
EVENT ofp_event->Switching_hub EventOFPPacketIn
packet in 2 d2:9e:d5:70:60:49 ff:ff:ff:ff:ff:ff 1
EVENT ofp_event->Switching_hub EventOFPPacketIn
packet in 2 0a:f3:9e:0d:5e:7d d2:9e:d5:70:60:49 3
EVENT ofp_event->Switching_hub EventOFPPacketIn
packet in 1 0a:f3:9e:0d:5e:7d d2:9e:d5:70:60:49 3
EVENT ofp_event->Switching_hub EventOFPPacketIn



Now again go in terminal 1 i.e mininet terminal in order to open xterm for h1 h2 h3 h4 

xterm h1 h2 h3 h4 


after this 4 xterms will be opened. we are using xterm to create 2 flooding scenario

In xterm H2 :

hping3 10.0.0.3 --flood --udp

using this command h2 will create an attack at 10.0.0.3 which is HOST3
Observe terminal 3 in which controller is run. you will be able to see flooding taking place in sdn.

Now type ping 10.0.0.3 in xterm h1 and h4.
we will get output as:

64 bytes from 10.0.0.3:icmp_seq1 ttl=64 time=0.198 ms 
64 bytes from 10.0.0.3:icmp_seq2 ttl=64 time=0.038 ms
64 bytes from 10.0.0.3:icmp_seq3 ttl=64 time=0.036 ms
64 bytes from 10.0.0.3:icmp_seq4 ttl=64 time=0.038 ms
64 bytes from 10.0.0.3:icmp_seq5 ttl=64 time=0.037 ms
64 bytes from 10.0.0.3:icmp_seq6 ttl=64 time=0.050 ms


This indicated that queue has been created at 10.0.0.3 as specified in our code and host 3 in not unreachable. To explain in details lets have a look at another scenario.

open xterm h1 and h4


In xterm x1 :

hping3 10.0.0.4 --flood --udp

using this command h1 will create an attack at 10.0.0.4 which is HOST4

now when you type pin 10.0.0.4 i  xterm h2 and h3 we will get output as follow:

from 10.0.0.2 icmp_seq=10 Destination Host Unreachable
from 10.0.0.2 icmp_seq=10 Destination Host Unreachable
from 10.0.0.2 icmp_seq=10 Destination Host Unreachable
from 10.0.0.2 icmp_seq=10 Destination Host Unreachable
from 10.0.0.2 icmp_seq=10 Destination Host Unreachable
from 10.0.0.2 icmp_seq=10 Destination Host Unreachable 
open new xterm h1 h1 h2 h2 

In order to observe bandwidth open all xterms and type the following commands accordingly :

In xterm 1(a) :
iperf -s -u -i 1 -p 5001

In xterm 1(b) :
iperf -s -u -i 1 -p 5002

In xterm 2(a) :
iperf -c 10.0.0.1 -p 5001 -u -b 1M

In xterm 2(b) :
iperf -c 10.0.0.1 -p 5002 -u -b 2M

output in xterm 1(a):
we are able to see interval (0.0-1.0 sec), Transfer (60.3kB, 58.9KB, 60.3KB .....), Bandwidth (495kbits/sec), jitter (11.494ms), lost/total datagrams(0%)

This is how we mitigate the DDOS attacks using the QoS regulation technique.
