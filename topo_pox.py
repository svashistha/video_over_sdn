#!/usr/bin/env python
 
from mininet.net  import Mininet
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.cli  import CLI
from mininet.util import quietRun
 
net = Mininet(link=TCLink);
 
# Add hosts and switches
h1 = net.addHost( 'h1', ip = '10.0.0.11', mac = '00:00:00:00:00:11' )
h2 = net.addHost( 'h2', ip = '10.0.0.22', mac = '00:00:00:00:00:22' )
h3 = net.addHost( 'h3', ip = '10.0.0.33', mac = '00:00:00:00:00:33')
h4 = net.addHost( 'h4', ip = '10.0.0.44', mac = '00:00:00:00:00:44')  
s1 = net.addSwitch( 's1',ip = '10.0.0.1',mac = '00:00:00:00:00:01')
s2 = net.addSwitch( 's2',ip = '10.0.0.2', mac = '00:00:00:00:00:02' )
s3 = net.addSwitch( 's3',ip = '10.0.0.3', mac = '00:00:00:00:00:03' )
s4 = net.addSwitch( 's4',ip = '10.0.0.4', mac = '00:00:00:00:00:04' )
s5 = net.addSwitch( 's5',ip = '10.0.0.5', mac = '00:00:00:00:00:05')
 
# Add links
# set link speeds to 10Mbit/s
linkopts = dict(bw=10)
net.addLink( h1, s1)
net.addLink( h2, s2)
net.addLink( s1, s2)
net.addLink( s1, s3)
net.addLink( s1, s5)
net.addLink( s3, s4)
net.addLink( s4, s2)
net.addLink( s5, s2)
net.addLink( s4, h3)
net.addLink( s5, h4)
 
# Start
net.addController('c', controller=RemoteController,ip='127.0.0.1',port=6633)
net.build()
net.start()
 
# CLI
CLI( net )
 
# Clean up
net.stop()
