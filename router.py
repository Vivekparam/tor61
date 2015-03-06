# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015

from collections import namedtuple
from enum import Enum

class TorRouter(object):
	# Router's state
	State = enum(init=0, running=1, stopped=2, failed=3)
	
	# router impl here
	RELAY_BEGIN = 0x01
	RELAY_DATA = 0x02
	RELAY_END = 0x03
	RELAY_CONNECTED = 0x04
	RELAY_EXTEND = 0x06
	RELAY_EXTENDED = 0x07
	RELAY_BEGIN_FAILED = 0x0b
	RELAY_EXTEND_FAILED = 0x0c

	RELAY_DIGEST_CONSTANT = 0x0000

	SOURCE_OUTGOING_C_ID = 1

	def __init__(self):
		self.router_ip_to_tor_objs = {}	# tuple -> Tor61Connection
		self.routing_table = {}
		self.state = State.init
		self.circuitbuildingstate = CircuitBuildingState.init

		# def relayExtendListener(ip, port):
		# 	#perform relay extend

		# x.addRelayExtendListener(relayExtendListener)

	# This brings up the router.
	# We contact the registration service,
	# establish ourselves, then build a circuit. 
	# Returns 1 on success, 0 on failure.
	# Q: should we have a while loop in start? or in startRouter.py
	# Q: should we allow a Tor61 connection listening thread on start? even if registration / constructing the circuit has failed?
	def start():
		# After constructing circuit,
		# Spawn a thread which listens for new
		# Tor61 connection attempts from others,
		# by calling startTorConnectionListener

		#contact registration service
		partner_host_addr = 
		# establish TCP 
		serverhost = partner_host_addr[1]
		port = int(partner_host_addr[2])
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect((serverhost, port))
		#s.send(header) s.recv(BUFFER_SIZE)
		# establish Tor61 connection for the circuit from source router
		tor61conection = Tor61Connection(partner_host_addr, socket, True)
		retval = tor61conection.startAsOpener(opener_agent_id, opened_agent_id)
			# loop the above until this successes...(but do we listen for tor61 is not sucess??)
		#	Create circuit
		retval = tor61conection.createCircuit()
		self.router_ip_to_tor_objs[partner_host_addr, tor61conection]
		self.sourceTor61Connection = tor61conection

		connect_handle_thread = threading.Thread(target=self.tor61Listener)
		connect_handle_thread.setDaemon(True)
		connect_handle_thread.start()

	# a thread that listens for new Tor61 connection
	# when a new Tor61 connection comes in, spawn a new thread to process and create a new Tor61 connection
	def tor61Listener():
		new_connection_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		host = new_connection_listener.gethostname()
		port_listening = 			# which port should we be listening
		new_connection_listener.bind((new_host, int(port_listening)))
		new_connection_listener.listen(5)
		# message_log("Router listening on " + socket.gethostbyname(socket.gethostname()) + ":" + port_listening)

		while self.state == State.running:
			(clientsocket, partneraddress) = new_connection_listener.accept()
			# we now have the new TCP
			# this thread creates new Tor61
			connection_handle_thread = threading.Thread(target=handle_tor61connection, args=(self, clientsocket, partneraddress,))
			connection_handle_thread.setDaemon(True)
			connection_handle_thread.start()

	# creates a new Tor61 connection 
	# blocks and listens for the OPEN cell
	# return OPENED cell
	# starts a reading and a writing thread for this connection
	def handle_tor61connection(clientsocket, partneraddress):
		tor61conection = Tor61Connection(partneraddress, clientsocket, False)
		tor61conection.startAsOpened()	# blocking call. waiting for open
		self.router_ip_to_tor_objs[partneraddress, tor61conection]

	# Constructs a stream to given host ip:port.
	# Takes as a parameter a tuple (host, hostport)
	# Returns tuple (1, stream_obj) if stream construction 
	# was successful.
	# Returns (0, None) otherwise
	def startStream(host_address):
		# pick a circuit
		tor61conection =  self.sourceTor61Connection
		c_id = tor61conection.getSourceOutgoingCircuitId()
		stream_obj = tor61conection.createNewStream
		if (!stream_obj):
			return (0, None)
		stream_obj.lockForConnected()
		tor61conection.sendRelay(c_id, stream_obj.streamNum, 0x0000, RELAY_BEGIN, host_address)
		stream_obj.waitForConnected(10)
		stream_obj.unlockForConnected()
		if (stream_obj.state != TorStream.State.running)
			return (0, None)
		return (1, stream_obj)

		# TODO
		# startStream will send a Relay Begin cell down the circuit, then start
		# a timer. If it does not recieve a response withing (10?) seconds, 
		# it will return 0, and proxy should treat this as an error.
		# If router gets back a Begin Failed, it also returns 0 and proxy treats this as an error.
		# If router gets back a Relay Connected, it sends back a 1, and proxy
		# sends back a 200 OK response. 


	# Listens on a port for incoming Tor61 connections
	# When one is built, constructs a Tor61Connection object
	# and puts it into the map router_ip_to_tor_objs
	def startTorConnectionListener(socket or something):

	def addProxy(proxy):
		self.proxy = proxy

	# Checks the circuit id of the cell and the socket it comes from,
	# look it up on the table to forward it to the appropiate Tor61 connection
	# host_addr should be a (host, host_port) tuple
	def lookUpRoutingTable(host_addr, c_id):
		# 	if it's in the routing table, return None otherwise
		return routing_table.get((host_addr, c_id))


	def forwardToTor61(redirect_tor61, cell, redirect_c_id):
		

	def handleCreated(cell):
		c_id, cell_type, padding = struct.unpack('>HBs')
		self.sourceTor61Connection.getCircuit(c_id).onCreate()
		# this is an error... we should only send create once and get created once... 

	def handleRelay(cell, tor61_partner_ip_port):
		c_id, cell_type, stream_id, zeroes, digest, body_length, relay_cmd, body_padding = struct.unpack('>HBHHIHBs')
		body = body_padding[:body_length]
		redirect_entry = lookUpRoutingTable(tor61_partner_ip_port, c_id)

		if (redirect_entry):	# forward it to the next
			redirect_tor61 = router_ip_to_tor_objs.get(redirect_entry.host_addr)
			forwardToTor61(redirect_tor61, cell, redirect_entry.c_id)

		else:	
			tor61conection = router_ip_to_tor_objs.get(tor61_partner_ip_port)
			if (relay_cmd == RELAY_BEGIN):			# for stream 
				# create a stream
				stream_obj = tor61conection.getCircuit(c_id).createStream(stream_id)
				tcp_host, tcp_host_port = body.split(':')
				# opens a TCP connection on the proxy side
				self.proxy.connect_to_server((tcp_host, tcp_host_port), stream_obj)	
				tor61conection.sendRelay(c_id, stream_id, RELAY_DIGEST_CONSTANT, RELAY_CONNECTED)

			elif (relay_cmd == RELAY_DATA):			# for stream
				stream_obj = tor61conection.getCircuit(c_id).getStream(stream_id)
				stream_obj.sendAllToProxy(body)

			elif (relay_cmd == RELAY_END):			# for stream
				stream_obj = tor61conection.getCircuit(c_id).getStream(stream_id)
				stream_obj.closeStream()

			elif (relay_cmd == RELAY_CONNECTED):	# for stream
				stream_obj = tor61conection.getCircuit(c_id).getStream(stream_id)
				stream_obj.notifyConnected()

			elif (relay_cmd == RELAY_EXTEND):		# for circuit
				tcp_host, tcp_host_port = body.split(':')
				findTor61Connection((tcp_host, tcp_host_port)))

			elif (relay_cmd == RELAY_EXTENDED):		# for circuit
				self.sourceTor61Connection.getCircuit(c_id).onRelayExtend()

			elif (relay_cmd == RELAY_BEGIN_FAILED):
				stream_obj = tor61conection.getCircuit(c_id).getStream(stream_id)
				stream_obj.notifyFailed()

			if ()
			else:
				stream_obj.sendAllToProxy(body)

		# if this tor connection exists
		# return
		# if not, create new
	def findTor61Connection(partner_host_address):

	def createNewTor






