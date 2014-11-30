from datetime import datetime
from pox.lib.revent.revent import EventMixin, Event
import pox.lib.util as util
from pox.core import core
import pox.openflow.libopenflow_01 as of
from collections import defaultdict
import pox.lib.packet as pkt
from collections import namedtuple
 
log = core.getLogger()
 
switches = {}
switch_ports = {}
adj = defaultdict(lambda:defaultdict(lambda:None))
 
mac_learning = {}
 
class ofp_match_withHash(of.ofp_match):
        ##Our additions to enable indexing by match specifications
        @classmethod
        def from_ofp_match_Superclass(cls, other):
                match = cls()
               
                match.wildcards = other.wildcards
                match.in_port = other.in_port
                match.dl_src = other.dl_src
                match.dl_dst = other.dl_dst
                match.dl_vlan = other.dl_vlan
                match.dl_vlan_pcp = other.dl_vlan_pcp
                match.dl_type = other.dl_type
                match.nw_tos = other.nw_tos
                match.nw_proto = other.nw_proto
                match.nw_src = other.nw_src
                match.nw_dst = other.nw_dst
                match.tp_src = other.tp_src
                match.tp_dst = other.tp_dst
                return match
               
        def __hash__(self):
                return hash((self.wildcards, self.in_port, self.dl_src, self.dl_dst, self.dl_vlan, self.dl_vlan_pcp, self.dl_type, self.nw_tos, self.nw_proto, self.nw_src, self.nw_dst, self.tp_src, self.tp_dst))
 
 
class Path(object):
        def __init__(self, src, dst, prev, first_port):
                self.src = src
                self.dst = dst
                self.prev = prev
                self.first_port = first_port
       
        def __repr__(self):
                ret = util.dpid_to_str(self.dst)
                u = self.prev[self.dst]
                while(u != None):
                        ret = util.dpid_to_str(u) + "->" + ret
                        u = self.prev[u]
               
                return ret                       
       
        def _tuple_me(self):
               
                list = [self.dst,]
                u = self.prev[self.dst]
                while u != None:
                        list.append(u)
                        u = self.prev[u]
                #log.debug("List path: %s", list)
                #log.debug("Tuple path: %s", tuple(list))
                return tuple(list)
       
        def __hash__(self):
                return hash(self._tuple_me())
       
        def __eq__(self, other):
                return self._tuple_me() == other._tuple_me()
 
def _get_path(src, dst):
#Input format        

        a = [["00:00:00:00:00:01", "00:00:00:00:00:02", "00:00:00:00:00:03", "00:00:00:00:00:04", "00:00:00:00:00:05", "00:00:00:00:00:11", "00:00:00:00:00:22", "00:00:00:00:00:33", "00:00:00:00:00:44"]
        ,[None, (10,4,2,2), (2,1,3,1), None, (4,3,4,1), (1,1,0,1), None, None, None]
        ,[(10,4,2,2), None, None, (2,1,3,2), (4,3,4,2), None, (1,1,1,0), None, None]
        ,[(2,1,1,3), None, None, (6,4,2,1), None,None, None, None,None]
        ,[None, (2,1,2,3), (6,4,1,2), None, None, None, None, (1,1,3,0), None]
        ,[(4,3,1,4), (4,3,2,4), None, None, None,None,None,None, (1,1,3,0)]
        ,[(1,1,1,0), None,None,None,None,None,None,None,None]
        ,[None,(1,1,1,0), None,None,None,None,None,None,None]
        ,[None,None,None,(1,1,3,0),None,None,None,None,None]
        ,[None,None,None,None,(1,1,3,0),None,None,None,None]]
        # src = 6
        # dst = 7
        graph = []
        graph2 = []
        portDictionary = {}
        delayMatrix = [[0]*9 for i in range(9)]
        costMatrix = [[0]*9 for i in range(9)]
        # src = 6
        # dst = 7

        def makeGraph(costMatrix):
                graph = []
                for source, sourceList in enumerate(costMatrix, start=0):
                        for destination, cost in enumerate(sourceList, start=0):
                                if cost == 0:
                                        continue
                                else:
                                        graph.append((source+1, destination+1, cost))
                return graph

        def calculateCostDelay(previous, costMatrix, delayMatrix, source, dest):
                totalDelay = 0        
                totalCost = 0
                currentNode = dest        
                previousNode = previous[currentNode]        
                path = []
                while currentNode is not None:
                        if currentNode == source:
                                path.insert(0,currentNode)
                                break
                        path.insert(0,currentNode)                        
                        totalDelay = totalDelay + delayMatrix[previousNode-1][currentNode-1]  
                        totalCost = totalCost + costMatrix[previousNode-1][currentNode-1]
                        currentNode = previousNode
                        previousNode = previous[currentNode]
                return totalCost, totalDelay, path

        for source , element in enumerate(a):
                for destination , node in enumerate(element):
                        if source is 0:
                                portDictionary[destination+1] = [node]
                        else:
                                if node is None:
                                        continue
                                else:
                                        graph.append((source, destination+1 , node[0]))
                                        graph2.append((source, destination+1, node[1]))                                
                                        delayMatrix[source-1][destination] = node[1]
                                        costMatrix[source-1][destination] = node[0]
                                        oldList = portDictionary[source]
                                        oldList.append((portDictionary[destination+1][0] , node[2], node[3]))
                                        portDictionary[source] = oldList


        # print graph
        # print graph2
        # print costMatrix
        # print delayMatrix

        inf = float('inf')
        Edge = namedtuple('Edge', 'start, end, cost')

        class Graph():
                def __init__(self, edges):
                        self.edges = edges2 = [Edge(*edge) for edge in edges]
                        self.vertices = set(sum(([e.start, e.end] for e in edges2), []))
                        return 
                def dijkstra(self, source, dest):               
                        assert source in self.vertices
                        dist = {vertex: inf for vertex in self.vertices}
                        previous = {vertex: None for vertex in self.vertices}
                        dist[source] = 0
                        q = self.vertices.copy()
                        neighbours = {vertex: set() for vertex in self.vertices}
                        for start, end, cost in self.edges:
                                neighbours[start].add((end, cost))
                        while q:                    
                                u = min(q, key=lambda vertex: dist[vertex])
                                q.remove(u)
                                if dist[u] == inf or u == dest:
                                        break
                                for v, cost in neighbours[u]:
                                        alt = dist[u] + cost
                                        if alt < dist[v]:                                  # Relax (u,v,a)
                                                dist[v] = alt
                                                previous[v] = u
                        s = []
                        first_port = None
                        v = dest
                        u = previous[v]
                        while u is not None:
                                if u == source:
                                        first_port = adj[u][v]                               
                                v = u
                                u = previous[v]  
                    	print previous
                    	print source
                    	print dest
                        return previous, first_port

        print graph
        graph = Graph(graph)
        graph_list = graph
        # graph2 = Graph(graph2)
        costPrevious, cost_first_port = graph.dijkstra(src, dst)        
        costPath = []
        totalDelayCost = 0        
        totalCostCost = 0
        currentNode = dst
        previousNode = costPrevious[currentNode]        
        while currentNode is not None:
                if currentNode == src:
                        costPath.insert(0,currentNode)
                        break
                costPath.insert(0,currentNode)                
                totalDelayCost = totalDelayCost + delayMatrix[previousNode-1][currentNode-1]
                # print currentNode
                # print previousNode
                totalCostCost = totalCostCost + costMatrix[previousNode-1][currentNode-1]
                currentNode = previousNode
                previousNode = costPrevious[currentNode]

        # print str(costPath) + " path"
        # print str(totalDelayCost) + " delay in path"
        # print str(totalCostCost) + " cost of path"

        if totalDelayCost <= 100: #change this delay accordingly
                #return path
                print str(costPath) + " path"
                print str(totalDelayCost) + " delay in path"
                print str(totalCostCost) + " cost of path"
                return Path(src,dst,costPrevious, cost_first_port)
        else:        
                graph2 = Graph(graph2)
                graph_list2 = graph2
                delayPrevious, delay_first_port = graph2.dijkstra(src,dst)
                delayPath = []
                totalDelayDelay = 0
                totalCostDelay = 0
                currentNode = dst
                previousNode = delayPrevious[currentNode]
                while currentNode is not None:
                        if currentNode == src:
                                delayPath.insert(0,currentNode)
                                break
                        delayPath.insert(0,currentNode)
                        totalDelayDelay = totalDelayDelay + delayMatrix[previousNode-1][currentNode-1]  
                        totalCostDelay = totalCostDelay + costMatrix[previousNode-1][currentNode-1]              
                        currentNode = previousNode
                        previousNode = delayPrevious[currentNode]

                # print str(delayPath) + " path"
                # print str(totalDelayDelay) + " delay in path"
                # print str(totalCostDelay) + " cost of path"

                if totalDelayDelay > 6:      #change this delay accordingly
                        print "No feasible solution"
                        return None
                else:
                        changeCostMatrix = costMatrix
                        changeDelayMatrix = delayMatrix
                        changeCostCost = totalCostCost
                        changeCostDelay = totalCostDelay
                        changeDelayCost = totalDelayCost
                        changeDelayDelay = totalDelayDelay
                        changeCostPath = costPath
                        changeDelayPath = delayPath
                        changeCostPrevious = costPrevious
                        changeDelayPrevious = delayPrevious
                        while True:                                        
                                change = (changeCostCost - changeCostDelay) / (changeDelayDelay - changeDelayCost)                          
                                for i in range(len(costMatrix)):
                                        for j in range(len(costMatrix)):                                        
                                                changeCostMatrix[i][j] = costMatrix[i][j] + change * delayMatrix[i][j]                        

                                newGraph = Graph(makeGraph(changeCostMatrix))
                                newPrevious, new_first_port = newGraph.dijkstra(src,dst)                        
                                changeCost, changeDelay, changePath = calculateCostDelay(newPrevious, changeCostMatrix, delayMatrix, src,dst)                        
                                newCostCost, newDelayCost, newCostPath = calculateCostDelay(costPrevious, changeCostMatrix, delayMatrix, src,dst)
                                if changeCost == newCostCost:
                                        print changePath
                                        print changeCost
                                        print changeDelay
                                        return Path(src, dst, newPrevious, new_first_port)
                                elif changeDelay <= 6:                                
                                        changeDelayPrevious = newPrevious
                                        changeCostDelay, changeDelayDelay, changeDelayPath = calculateCostDelay(changeDelayPrevious, costMatrix, delayMatrix, src,dst)
                                else:                                
                                        changeCostPrevious = newPrevious
                                        changeCostCost, changeDelayCost, changeCostPath = calculateCostDelay(changeCostPrevious, costMatrix, delayMatrix, src,dst)

        return None
 
 
def _install_path(prev_path, match):
        dst_sw = prev_path.dst
        cur_sw = prev_path.dst
        dst_pck = match.dl_dst
       
        msg = of.ofp_flow_mod()
        msg.match = match
        msg.idle_timeout = 10
        msg.flags = of.OFPFF_SEND_FLOW_REM     
        msg.actions.append(of.ofp_action_output(port = mac_learning[dst_pck].port))
        log.debug("Installing forward from switch %s to output port %s", util.dpid_to_str(cur_sw), mac_learning[dst_pck].port)
        switches[dst_sw].connection.send(msg)
       
        next_sw = cur_sw
        cur_sw = prev_path.prev[next_sw]
        while cur_sw is not None: #for switch in path.keys():
                msg = of.ofp_flow_mod()
                msg.match = match
                msg.idle_timeout = 10
                msg.flags = of.OFPFF_SEND_FLOW_REM
                log.debug("Installing forward from switch %s to switch %s output port %s", util.dpid_to_str(cur_sw), util.dpid_to_str(next_sw), adj[cur_sw][next_sw])
                msg.actions.append(of.ofp_action_output(port = adj[cur_sw][next_sw]))
                switches[cur_sw].connection.send(msg)
                next_sw = cur_sw
               
                cur_sw = prev_path.prev[next_sw]
 
               
def _print_rev_path(dst_pck, src, dst, prev_path):
        str = "Reverse path from %s to %s over: [%s->dst over port %s]" % (util.dpid_to_str(src), util.dpid_to_str(dst), util.dpid_to_str(dst), mac_learning[dst_pck].port)
        next_sw = dst
        cur_sw = prev_path[next_sw]
        while cur_sw != None: #for switch in path.keys():
                str += "[%s->%s over port %s]" % (util.dpid_to_str(cur_sw), util.dpid_to_str(next_sw), adj[cur_sw][next_sw])
                next_sw = cur_sw
                cur_sw = prev_path[next_sw]
               
        log.debug(str)
 
 
class NewFlow(Event):
        def __init__(self, prev_path, match, adj):
                Event.__init__(self)
                self.match = match
                self.prev_path = prev_path
                self.adj = adj
       
class Switch(EventMixin):
        _eventMixin_events = set([
                                                        NewFlow,
                                                        ])
        def __init__(self, connection):
                self.connection = connection
                connection.addListeners(self)
                for p in self.connection.ports.itervalues(): #Enable flooding on all ports until they are classified as links
                        self.enable_flooding(p.port_no)
       
        def __repr__(self):
                return util.dpid_to_str(self.connection.dpid)
       
       
        def disable_flooding(self, port):
                msg = of.ofp_port_mod(port_no = port,
                                                hw_addr = self.connection.ports[port].hw_addr,
                                                config = of.OFPPC_NO_FLOOD,
                                                mask = of.OFPPC_NO_FLOOD)
       
                self.connection.send(msg)
       
 
        def enable_flooding(self, port):
                msg = of.ofp_port_mod(port_no = port,
                                                        hw_addr = self.connection.ports[port].hw_addr,
                                                        config = 0, # opposite of of.OFPPC_NO_FLOOD,
                                                        mask = of.OFPPC_NO_FLOOD)
       
                self.connection.send(msg)
       
        def _handle_PacketIn(self, event):
                def forward(port):
                        """Tell the switch to forward the packet"""
                        msg = of.ofp_packet_out()
                        msg.actions.append(of.ofp_action_output(port = port))       
                        if event.ofp.buffer_id is not None:
                                msg.buffer_id = event.ofp.buffer_id
                        else:
                                msg.data = event.ofp.data
                        msg.in_port = event.port
                        self.connection.send(msg)
                               
                def flood():
                        """Tell all switches to flood the packet, remember that we disable inter-switch flooding at startup"""
                        #forward(of.OFPP_FLOOD)
                        for (dpid,switch) in switches.iteritems():
                                msg = of.ofp_packet_out()
                                if switch == self:
                                        if event.ofp.buffer_id is not None:
                                                msg.buffer_id = event.ofp.buffer_id
                                        else:
                                                msg.data = event.ofp.data
                                        msg.in_port = event.port
                                else:
                                        msg.data = event.ofp.data
                                ports = [p for p in switch.connection.ports if (dpid,p) not in switch_ports]
                                if len(ports) > 0:
                                        for p in ports:
                                                msg.actions.append(of.ofp_action_output(port = p))
                                        switches[dpid].connection.send(msg)
                               
                               
                def drop():
                        """Tell the switch to drop the packet"""
                        if event.ofp.buffer_id is not None: #nothing to drop because the packet is not in the Switch buffer
                                msg = of.ofp_packet_out()
                                msg.buffer_id = event.ofp.buffer_id
                                event.ofp.buffer_id = None # Mark as dead, copied from James McCauley, not sure what it does but it does not work otherwise
                                msg.in_port = event.port
                                self.connection.send(msg)
               
                #log.debug("Received PacketIn")          
                packet = event.parsed
                               
                SwitchPort = namedtuple('SwitchPoint', 'dpid port')
               
                if (event.dpid,event.port) not in switch_ports:                                               # only relearn locations if they arrived from non-interswitch links
                        mac_learning[packet.src] = SwitchPort(event.dpid, event.port)   #relearn the location of the mac-address
               
                if packet.effective_ethertype == packet.LLDP_TYPE:
                        drop()
                        log.debug("Switch %s dropped LLDP packet", self)
                elif packet.dst.is_multicast:
                        flood()
                        #log.debug("Switch %s flooded multicast 0x%0.4X type packet", self, packet.effective_ethertype)
                elif packet.dst not in mac_learning:
                        flood() #Let's first learn the location of the recipient before generating and installing any rules for this. We might flood this but that leads to further complications if half way the flood through the network the path has been learned.
                        log.debug("Switch %s flooded unicast 0x%0.4X type packet, due to unlearned MAC address", self, packet.effective_ethertype)
                elif packet.effective_ethertype == packet.ARP_TYPE:
                        #These packets are sent so not-often that they don't deserve a flow
                        #Instead of flooding them, we drop it at the current switch and have it resend by the switch to which the recipient is connected.
                        #flood()
                        drop()
                        dst = mac_learning[packet.dst]
                        #print dst.dpid, dst.port
                        msg = of.ofp_packet_out()
                        msg.data = event.ofp.data
                        msg.actions.append(of.ofp_action_output(port = dst.port))
                        switches[dst.dpid].connection.send(msg)
                        log.debug("Switch %s processed unicast ARP (0x0806) packet, send to recipient by switch %s", self, util.dpid_to_str(dst.dpid))
                else:
                        log.debug("Switch %s received PacketIn of type 0x%0.4X, received from %s.%s", self, packet.effective_ethertype, util.dpid_to_str(event.dpid), event.port)
                        dst = mac_learning[packet.dst]
                        prev_path = _get_path(self.connection.dpid, dst.dpid)
                        if prev_path is None:
                                flood()
                                return
                        log.debug("Path from %s to %s over path %s", packet.src, packet.dst, prev_path)
                       
                        match = ofp_match_withHash.from_packet(packet)
                        _install_path(prev_path, match)
                       
                        #forward the packet directly from the last switch, there is no need to have the packet run through the complete network.
                        drop()
                        dst = mac_learning[packet.dst]
                        msg = of.ofp_packet_out()
                        msg.data = event.ofp.data
                        msg.actions.append(of.ofp_action_output(port = dst.port))
                        switches[dst.dpid].connection.send(msg)
                       
                        self.raiseEvent(NewFlow(prev_path, match, adj))
                        log.debug("Switch %s processed unicast 0x%0.4x type packet, send to recipient by switch %s", self, packet.effective_ethertype, util.dpid_to_str(dst.dpid))
                       
               
        def _handle_ConnectionDown(self, event):
                log.debug("Switch %s going down", util.dpid_to_str(self.connection.dpid))
                del switches[self.connection.dpid]
                #pprint(switches)
 
               
class NewSwitch(Event):
        def __init__(self, switch):
                Event.__init__(self)
                self.switch = switch
 
 
class Forwarding(EventMixin):
        _core_name = "myforwarding"
        _eventMixin_events = set([NewSwitch,])
       
        def __init__ (self):
                log.debug("Forwarding is initialized")
                               
                def startup():
                        core.openflow.addListeners(self)
                        core.openflow_discovery.addListeners(self)
                        log.debug("Forwarding started")
               
                core.call_when_ready(startup, 'openflow', 'openflow_discovery')
                       
        def _handle_LinkEvent(self, event):
                link = event.link
                if event.added:
                        log.debug("Received LinkEvent, Link Added from %s to %s over port %d", util.dpid_to_str(link.dpid1), util.dpid_to_str(link.dpid2), link.port1)
                        adj[link.dpid1][link.dpid2] = link.port1
                        switch_ports[link.dpid1,link.port1] = link
                else:
                        log.debug("Received LinkEvent, Link Removed from %s to %s over port %d", util.dpid_to_str(link.dpid1), util.dpid_to_str(link.dpid2), link.port1)
               
        def _handle_ConnectionUp(self, event):
                log.debug("New switch connection: %s", event.connection)
                sw = Switch(event.connection)
                switches[event.dpid] = sw;
                self.raiseEvent(NewSwitch(sw))
 
def launch (postfix=datetime.now().strftime("%Y%m%d%H%M%S")):
        from log.level import launch
        launch(DEBUG=True)
 
        from samples.pretty_log import launch
        launch()
 
        #from openflow.keepalive import launch
        #launch(interval=15) # 15 seconds
 
        from openflow.discovery import launch
        launch()
 
        core.registerNew(Forwarding)
