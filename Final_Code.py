from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from operator import attrgetter
from ryu.lib import hub
import requests,json


class Switching_hub(app_manager.RyuApp):
  #OpenFlow protocol version is specified
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Switching_hub, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.switches = set() 
        self.dp1 = True
        self.dp2 = True
     #thread is initialized to periodically issue a request
     # hub.spawn() is used to create threads
        self.monitor_thread = hub.spawn(self._monitor)
        
#decorator to obtain the switch features        
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.switches.add(datapath) 
        dpid= str(datapath.id)
        dp_Str = "000000000000000"+dpid 
        #ovsdb_addr is set to access OVSDB
        connection = "tcp:127.0.0.1:6632"
        print "PUT the Request",requests.put(url="http://localhost:8080/v1.0/conf/switches/"+ dp_Str +"/ovsdb_addr",data=json.dumps(connection))
        print dpid
        # install table-miss flow entry
        # We specify NO BUFFER to max_len of the output action
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, 
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)


#to add the flow entry into switch
    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            flow_mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id, 
                                         priority=priority, match=match, 
                                         instructions=inst, table_id=1)
        else:
            flow_mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                         match=match, instructions=inst, table_id=1)
        datapath.send_msg(flow_mod)
     

#this decorator is to handle the stats reply about queue
    @set_ev_cls(ofp_event.EventOFPQueueGetConfigReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        print "datapath response for queue",(ev.msg.queues),ev.msg.datapath

#decorator to handle packet in messages
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # mac address learn to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD
        actions = [parser.OFPActionOutput(out_port)]
        
        #setup of queue rules manually for switch 1 & switch 2
        if   dpid==1 and src=="00:00:00:00:00:01":
            actions.append(parser.OFPActionSetQueue(1))
        elif dpid==1 and src=="00:00:00:00:00:02":
            actions.append(parser.OFPActionSetQueue(0))
        elif dpid==2 and dst=="00:00:00:00:00:01":
            actions.append(parser.OFPActionSetQueue(1))
        elif dpid==2 and dst=="00:00:00:00:00:02":
            actions.append(parser.OFPActionSetQueue(0)) 

        # installing flows to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
        
        #defining queues for switch 1 in topology
            if(dpid==1 and self.dp1):
                self.dp1=False
                print("Queues Set Up for",dpid)

                data={"port_name": "s1-eth1","max_rate": "1000000", "queues":[{"max_rate":"500000"}, {"min_rate": "800000"}]}
                url="http://localhost:8080/qos/queue/0000000000000001"
                print "Post the Request",requests.post(url=url,data=json.dumps(data))
                
                req = parser.OFPQueueGetConfigRequest(datapath, 1);
                print "Queue Req sent for ID",datapath.id
                datapath.send_msg(req)

                data={"port_name": "s1-eth2","max_rate": "1000000","queues": [{"max_rate":"300000"}, {"min_rate": "800000"}]}
                url="http://localhost:8080/qos/queue/0000000000000001"
                print "Post the Request",requests.post(url=url,data=json.dumps(data))
                
                req = parser.OFPQueueGetConfigRequest(datapath, 1);
                print "Queue Req sent for ID",datapath.id
                datapath.send_msg(req)
                
                #qos setup for switch s1,dest h3 flow entry 
                url="http://127.0.0.1:8080/qos/rules/0000000000000001"
                data ={"match": {"nw_dst":"10.0.0.3","nw_proto":"UDP"},"actions":{"queue":0},"priority":100}
                print "Post the request",requests.post(url=url,data=json.dumps(data))
                print "GET Request",requests.get(url=url)
 
                #qos setup for switch s1,dest h3 flow entry
                url="http://127.0.0.1:8080/qos/rules/0000000000000001"
                data ={"match": {"nw_dst":"10.0.0.3","nw_proto":"UDP"},"actions":{"queue":1},"priority":100}
                print "Post the Request",requests.post(url=url,data=json.dumps(data))
                print "GET Request",requests.get(url=url)

          #defining queues for switch 2 in topology
            if(dpid==2 and self.dp2):
                self.dp2=False
                print("Queues Set Up for",dpid)

                data={"port_name":"s2-eth1","max_rate": "1000000", "queues": [{"max_rate":"500000"}, {"min_rate": "800000"}]}
                url="http://localhost:8080/qos/queue/0000000000000002"
                print "Post the Request",requests.post(url=url,data=json.dumps(data))
                
                req =parser.OFPQueueGetConfigRequest(datapath, 2);
                print "Queue Req sent for ID",datapath.id
                datapath.send_msg(req) 

                data={"port_name":"s2-eth2","max_rate": "1000000", "queues": [{"max_rate":"200000"}, {"min_rate": "800000"}]}
                url="http://localhost:8080/qos/queue/0000000000000002"
                print "Post the request",requests.post(url=url,data=json.dumps(data))

                req = parser.OFPQueueGetConfigRequest(datapath, 2);
                print "Queue Req sent for ID",datapath.id
                datapath.send_msg(req)
 
                #qos setup for switch s2,dest h3 flow entry
                url="http://127.0.0.1:8080/qos/rules/0000000000000002"
                data = {"match":{"nw_dst":"10.0.0.3","nw_proto":"UDP"},"actions":{"queue":0},"priority":100}
                print "Post the Request",requests.post(url=url,data=json.dumps(data))
                print "GET Request",requests.get(url=url) 

                #qos setup for switch s2, dest h3 flow entry
                url="http://127.0.0.1:8080/qos/rules/0000000000000002"
                data = {"match": {"nw_dst":"10.0.0.3","nw_proto":"UDP"},"actions":{"queue":1},"priority":100}
                print "Post the Request",requests.post(url=url,data=json.dumps(data))
                print "GET Request",requests.get(url=url)


            # verify if we have a valid buffer_id
            # Valid buffer id is used to avoid sending flow_mod &
            # packet_out messages

            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 2, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 2, match, actions)
        
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        output = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                     in_port=in_port, actions=actions, data=data)
        datapath.send_msg(output)


#event is used for detecting connection and disconnection
    @set_ev_cls(ofp_event.EventOFPStateChange,[MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        #switch is registered as the monitor target
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        #switch registration is deleted
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]


#to obtain statistical info about registered switch infinitely every 5 seconds
    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(5)

#to request the port stats 
    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)


#handles the received response from the switch about it's port status
    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body 

        self.logger.info('datapath       port          '
                         'rx-pkts    rx-bytes   rx-errors '
                         'tx-pkts    tx-bytes   tx-errors ')
        self.logger.info('-------------------------------- '
                         '-------------------------------- '
                         '-------------------------------- ')
        
        for stat in sorted(body, key=attrgetter('port_no')):
            self.logger.info('%016x  %8x  %8d  %8d  %8d  %8d  %8d  %8d ',
                            ev.msg.datapath.id,  stat.port_no,
                            stat.rx_packets, stat.rx_bytes, stat.rx_errors, 
                            stat.tx_packets, stat.tx_bytes, stat.tx_errors)

            #condition to drop the packets from that port
            if (((stat.rx_packets-stat.tx_packets) > 20000) or ((stat.tx_packets-stat.rx_packets) > 20000)):
                print("Flooding Recognised....")
                print("Packet dropped")
                msg = ev.msg
                datapath = msg.datapath
                ofproto = datapath.ofproto
                parser = datapath.ofproto_parser
                action =[]
                match = parser.OFPMatch(in_port=stat.port_no)
                self.add_flow(datapath, 10 , match, action)
