# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015

from collections import namedtuple
from subprocess import Popen, PIPE
import sys
import threading
import socket

class TorRouter(object):
	# Router's state
	class State(object):
		init = 0
		running = 1
		stopped = 2
		failed = 3
	
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

	def __init__(self ):
		self.router_ip_to_tor_objs = {}	# tuple -> Tor61Connection
		self.routing_table = {}			# ((ip, port), c_id) ->  ((ip, port), c_id) 
		self.state = TorRouter.State.init
		self.group_number = sys.argv[1]
		self.router_instance_number = sys.argv[2]
		self.port_listening_tor61 = sys.argv[3]			# which port should we be listening

		# def relayExtendListener(ip, port):
		# 	#perform relay extend

		# x.addRelayExtendListener(relayExtendListener)


	# This brings up the router.
	# We contact the registration service,
	# establish ourselves, then build a circuit. 
	# Returns 1 on success, 0 on failure.
	def start(self):
		print 'router start'
		# After constructing circuit,
		# Spawn a thread which listens for new
		# Tor61 connection attempts from others,
		# by calling startTorConnectionListener

		# fork + exec to contact registration service
		connect_handle_thread = threading.Thread(target=self.tor61Listener)
		connect_handle_thread.setDaemon(True)
		connect_handle_thread.start()

		retval = -1
		tor61connection = None
		while (retval < 0):	
			# TODO: Get list of possible hosts from registration
			# service, pick one at random as partner_host_addr

			p = Popen(['python', 'registrationUtility/fetch.py', 'Tor61Router-' + str(self.group_number)], stdin=PIPE, stdout=PIPE, stderr=PIPE)
			output, err = p.communicate()
			print output
			lines = output.split('\n')
			if (len(lines) < 4):
				#print 'not enough routers available ' + str(len(lines))
				#print lines[0]
				continue
			line = lines[0].split(' ')

			partner_host_addr = (line[0], line[1])
			# establish TCP 
			socket = createTCPConnection(partner_host_addr)
			(retval, tor61connection) = createTor61Connection(partner_host_addr, socket, True)
			print 'retval: '+ str(retval)

		# 	build our first tor61connection
		self.sourceTor61Connection = tor61connection

		#	Create circuit -- this blocks until response or timeout
		retval, circuit_obj = self.sourceTor61Connection.sendCreate(True)
		if(retval != 1):
			print "Error -- sendCreate did not succeed. Error code: ", retval
			return

		line = lines[1].split(' ')
		secondHopAddr = (line[0], line[1]) # "ip:por0<agentid>", get from registration

		circuit_obj.receive_relayextend_condition.acquire()
		retval = self.sourceTor61Connection.sendRelay(circuit_obj.getCid, TorStream.STREAM_ZERO_RELAY_EXTEND, 
			RELAY_DIGEST_CONSTANT, len(secondHopAddr), RELAY_EXTEND, secondHopAddr) # 	def sendRelay(self, c_id, stream_id, digest, relay_cmd, body):
		circuit_obj.receive_relayextend_condition.wait(10)
		circuit_obj.receive_relayextend_condition.release()

		line = lines[2].split(' ')
		thirdHopAddr  (line[0], line[1])# "ip:por0<agentid>", get from registration
		circuit_obj.receive_relayextend_condition.acquire()
		retval = self.sourceTor61Connection.sendRelay(circuit_obj.getCid, TorStream.STREAM_ZERO_RELAY_EXTEND, 
			RELAY_DIGEST_CONSTANT, len(thirdHopAddr), RELAY_EXTEND, thirdHopAddr) # 	def sendRelay(self, c_id, stream_id, digest, relay_cmd, body):
		circuit_obj.receive_relayextend_condition.wait(10)
		circuit_obj.receive_relayextend_condition.release()

		if (circuit_obj.state == Circuit.State.three_hop):
			print 'building circuit done'



	# a thread that listens for new Tor61 connection
	# registers this own router
	# when a new Tor61 connection comes in, spawn a new thread to process and create a new Tor61 connection
	def tor61Listener(self):
		print 'tor61Listener'
		new_connection_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		host = socket.gethostname()

		new_connection_listener.bind((host, int(self.port_listening_tor61)))
		new_connection_listener.listen(5)
		# message_log("Router listening on " + socket.gethostbyname(socket.gethostname()) + ":" + port_listening)
		# register ourselves
		
		router_instance_name = 'Tor61Router-' + str(self.group_number) + '-' + str(self.router_instance_number)
		int_data = 65539
		p = Popen(['python', 'registrationUtility/registration_client.py', str(self.port_listening_tor61), router_instance_name, str(int_data)])
					# stdin=PIPE, stdout=PIPE, stderror=PIPE)

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
		createTor61Connection(partneraddress, clientsocket, False)
		
		
	# Constructs a stream to given host ip:port.
	# Takes as a parameter a tuple (host, hostport)
	# Returns tuple (1, stream_obj) if stream construction 
	# was successful.
	# Returns (0, None) otherwise
	def startStream(host_address):
		# pick a circuit
		tor61conection =  self.sourceTor61Connection
		c_id = tor61conection.getSourceOutgoingCircuitId()
		stream_obj = tor61conection.getCircuitObj(c_id).createStream()
		if not stream_obj:
			return (0, None)
		stream_obj.lockForConnected()
		tor61conection.sendRelay(c_id, stream_obj.streamNum, 0x0000, RELAY_BEGIN, host_address)
		stream_obj.waitForConnected(10)
		stream_obj.unlockForConnected()
		if (stream_obj.state != TorStream.State.running):
			return (0, None)
		return (1, stream_obj)

		# TODO
		# startStream will send a Relay Begin cell down the circuit, then start
		# a timer. If it does not recieve a response withing (10?) seconds, 
		# it will return 0, and proxy should treat this as an error.
		# If router gets back a Begin Failed, it also returns 0 and proxy treats this as an error.
		# If router gets back a Relay Connected, it sends back a 1, and proxy
		# sends back a 200 OK response. 

	def addProxy(self, proxy):
		self.proxy = proxy

	# Checks the circuit id of the cell and the socket it comes from,
	# look it up on the table to forward it to the appropiate Tor61 connection
	# host_addr should be a (host, host_port) tuple
	def lookUpRoutingTable(host_addr, c_id):
		return routing_table.get((host_addr, c_id))

	def forwardToTor61(redirect_tor61, cell, redirect_c_id):
		# TODO change the c_id, repack the cell 
		redirect_tor61.sendRelayCell(cell)

	def handleCreated(cell):
		c_id, cell_type, padding = struct.unpack('>HBs')
		self.sourceTor61Connection.getCircuit(c_id).onCreate()
		# this is an error... we should only send create once and get created once... 

	def handleRelay(cell, tor61_partner_ip_port):
		c_id, cell_type, stream_id, zeroes, digest, body_length, relay_cmd, body_padding = struct.unpack('>HBHHIHBs')
		body = body_padding[:body_length]
		redirect_entry = lookUpRoutingTable(tor61_partner_ip_port, c_id)

		if (redirect_entry):	# forward it to the next
			redirect_entry = (host_addr, c_id)
			redirect_tor61 = router_ip_to_tor_objs.get(host_addr)
			forwardToTor61(redirect_tor61, cell, c_id)

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

			elif (relay_cmd == RELAY_EXTEND):		# for circuit, create new outgoing circuit
				tcp_host, tcp_host_port = body.split(':')
				tor61 = findTor61Connection((tcp_host, tcp_host_port))
				circuit_obj = None
				if (tor61):
					circuit_obj = tor61.sendCreate(False)
				else: 
					createTCPConnection((tcp_host, tcp_host_port))
					(retval, tor61) = createTor61Connection((tcp_host, tcp_host_port))
					circuit_obj = tor61.sendCreate(False)
				# above blocks until we have received created
				if (circuit_obj): 
					circuit_obj.receive_relayextend_condition.acquire()
					c_id, stream_id, digest, relay_cmd, body
					tor61.sendRelay(c_id, stream_id, digest, 0, RELAY_EXTENDED, '')
					circuit_obj.receive_relayextend_condition.wait(10)
					circuit_obj.receive_relayextend_condition.release()
				# else : (got CREATE FAILED) do nothing?? 

			elif (relay_cmd == RELAY_EXTENDED):		# for circuit
				source_c_id = self.getSourceOutgoingCircuitId
				if (source_c_id != c_id):
					print "Getting a RELAY EXTENDED should be meant for itself, but wrong c_id"
					return
				self.sourceTor61Connection.getCircuit(c_id).onRelayExtended()
				circuit_obj.receive_relayextend_condition.acquire()
				circuit_obj.receive_relayextend_condition.notify(10)
				circuit_obj.receive_relayextend_condition.release()

			elif (relay_cmd == RELAY_BEGIN_FAILED):	# for stream
				stream_obj = tor61conection.getCircuit(c_id).getStream(stream_id)
				stream_obj.notifyFailed()

			else:		
				print "error. no such Relay cell type"

	# return this tor connection if exists, otherwise None
	def findTor61Connection(self, partner_host_address):
		return router_ip_to_tor_objs[partner_host_address]

	def createTCPConnection(self, partner_host_addr):
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect(partner_host_addr)
		return s
	# partner_host_addr = (host, port)
	def createTor61Connection(self, partner_host_addr, socket, we_are_initiator):
		# establish Tor61 connection for the circuit from source router
		tor61conection = Tor61Connection(partner_host_addr, socket, we_are_initiator)
		tor61conection.addOnRelayHandler(self.handleRelay)
		if (we_are_initiator):
			retval = tor61conection.startAsOpener(opener_agent_id, opened_agent_id)
		else:
			retval = tor61conection.startAsOpened() 	# blocking call. waiting for open
		if (retval > 0):
			self.router_ip_to_tor_objs[partner_host_addr, tor61conection]
			# loop the above until this successes...(but do we listen for tor61 is not sucess??)
		return (retval, tor61conection)


