# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015

from collections import namedtuple
from subprocess import Popen, PIPE
from tor61connection import Tor61Connection
from stream import TorStream
from circuit import Circuit
import sys
import threading
import socket
import struct
import random
from pprint import pprint

class TorRouter(object):
	# Router's state
	class State(object):
		init = 0
		running = 1
		stopped = 2
		failed = 3
	
	CELL_TYPE_CREATE = 0x01

	# router impl here
	RELAY_BEGIN = 0x01
	RELAY_DATA = 0x02
	RELAY_END = 0x03
	RELAY_CONNECTED = 0x04
	RELAY_EXTEND = 0x06
	RELAY_EXTENDED = 0x07
	RELAY_BEGIN_FAILED = 0x0b
	RELAY_EXTEND_FAILED = 0x0c

	RELAY_DIGEST_CONSTANT = 0

	SOURCE_OUTGOING_C_ID = 1

	def __init__(self):
		self.router_ip_to_tor_objs = {}	# tuple -> Tor61Connection
		self.routing_table = {}			# ((ip, port), c_id) ->  ((ip, port), c_id) 
		self.state = TorRouter.State.init
		self.group_number = sys.argv[1]
		self.router_instance_number = sys.argv[2]
		self.port_listening_tor61 = self.get_open_port()			# which port should we be listening
		self.agent_id = (int(self.group_number) << 16) | int(self.router_instance_number)

		self.next_socket_num = 1
		self.next_socket_num_lock = threading.Lock()
		self.router_ip_to_tor_objs_lock = threading.Lock()
		self.routing_table_lock = threading.Lock()
		self.connecting_to_tor_routers = '' #self.group_number #"7244"

	def addPartnerToRouterIPTorMap(self, partner_host_addr, tor61connection):
		self.router_ip_to_tor_objs_lock.acquire()
		self.router_ip_to_tor_objs[partner_host_addr] = tor61connection
		self.router_ip_to_tor_objs_lock.release()

	def removePartnerFromRouterIPTorMap(self, partner_host_addr):
		self.router_ip_to_tor_objs_lock.acquire()
		self.router_ip_to_tor_objs.pop(partner_host_addr, None) # get rid of KeyError
		self.router_ip_to_tor_objs_lock.release()

	def addPartnerToRoutingTable(self, incoming_tuple, outgoing_tuple):
		self.routing_table_lock.acquire()
		self.routing_table[incoming_tuple] = outgoing_tuple
		self.routing_table_lock.release()

	def removePartnerFromRoutingTable(self, partner_host_addr, c_id):
		self.routing_table_lock.acquire()
		self.routing_table.pop((partner_host_addr, c_id))
		self.routing_table_lock.release()

	def exit(self):
		for key in self.router_ip_to_tor_objs:
			tor61connection = self.router_ip_to_tor_objs[key]
			tor61connection.sendDestroy()
		print "router exit"

	# This brings up the router.
	# We contact the registration service,
	# establish ourselves, then build a circuit. 
	# Returns 1 on success, <0 on failure.
	def start(self):
		print 'router start'
		# After constructing circuit,
		# Spawn a thread which listens for new
		# Tor61 connection attempts from others,
		# by calling startTorConnectionListener
		self.state = TorRouter.State.running
		connect_handle_thread = threading.Thread(target=self.tor61Listener)
		connect_handle_thread.setDaemon(True)
		connect_handle_thread.start()

		retval = -1
		tor61connection = None
		router_circuit_arr = []
		while (retval < 0):	
			try: 
				# TODO: Get list of possible hosts from registration
				# service, pick one at random as partner_host_addr
				print "Trying to connect to 1st hop router:"
				print "Getting a list from Registration Utility..."
				p = Popen(['python', 'registrationUtility/fetch.py', 'Tor61Router-' + str(self.connecting_to_tor_routers)], stdin=PIPE, stdout=PIPE, stderr=PIPE)
				output, err = p.communicate() # lol error
				print err
				# output = "128.208.2.207	42375	65537\n"
				# output = "128.208.1.159\t3333\t474745784\n"
				print output
				lines = output.split('\n')

				if (len(lines) > 1):
					rand = random.randint(0, len(lines) - 2)
					line = lines[rand].split('\t')
					partner_host_addr = (line[0], int(line[1]))
					print "Attempting to connect TCP to :" + str(partner_host_addr)
					# establish TCP 
					socket = TorRouter.createTCPConnection(partner_host_addr)
					if socket is None:
						retval = -1
						continue
					(retval, tor61connection) = self.createTor61Connection( partner_host_addr, socket, True, 
																			opener_agent_id=self.agent_id, opened_agent_id=line[2])
					print "our agent id: ", self.agent_id
					router_circuit_arr.append(partner_host_addr)
					# 	build our first tor61connection
					self.sourceTor61Connection = tor61connection
					#	Create circuit -- this blocks until response or timeout
					self.addPartnerToRouterIPTorMap(partner_host_addr, tor61connection)
					retval, circuit_obj = self.sourceTor61Connection.sendCreate(True)
					if (retval != 1):
						print "Error -- sendCreate did not succeed. Error code: ", retval, ". Try a new router..."
						retval = -1
			except IndexError:
				self.killRouter()
				print "index error"

		count = 2
		while (count < 4):
			print "Trying to connect to " , str(count), " hop router:"
			p = Popen(['python', 'registrationUtility/fetch.py', 'Tor61Router-' + str(self.connecting_to_tor_routers)], stdin=PIPE, stdout=PIPE, stderr=PIPE)
			output, err = p.communicate() 
			print err
			# if (count == 3):
			# 	output = "128.208.2.207	42375	65537\n"
				# output = "128.208.1.159\t3333\t474745784\n"
			# if (i == 1):
			# 	output = "128.208.2.207	42375	65537\n"

			# print output
			lines = output.split('\n')
			rand = random.randint(0, len(lines) - 2)
			line = lines[rand].split('\t')
			secondHopAddr = (line[0], line[1]) # "ip:por0<agentid>", get from registration
		
			body_message = line[0] + ":" + line[1] + "\0"
			body_message = struct.pack('>%dsI' % (len(body_message),), body_message, int(line[2]))
			circuit_obj.receive_relayextend_condition.acquire()
			circuit_obj.receive_relayextend_condition.success = 0
			self.sourceTor61Connection.sendRelay(circuit_obj.getCid(), TorStream.STREAM_ZERO_RELAY_EXTEND, 
				TorRouter.RELAY_DIGEST_CONSTANT, len(body_message), TorRouter.RELAY_EXTEND, body_message) 
			circuit_obj.receive_relayextend_condition.wait(10)
			circuit_obj.receive_relayextend_condition.release()

			if(circuit_obj.receive_relayextend_condition.success == 0):			# keep looping
				print "Error -- sendRelayExtend did not succeed. Try a new router..."
			else:
				router_circuit_arr.append(secondHopAddr)
				count = count + 1

		if (circuit_obj.state == Circuit.State.three_hop):
			print 'building circuit done: '
			pprint(router_circuit_arr)
			return 1
		else:
			print "CIRCUIT STATE INVALID"
			return -1

	def get_open_port(self):
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.bind(("",0))
		s.listen(1)
		port = s.getsockname()[1]
		s.close()
		return port

	def killRouter(self):
		self.registrationUtil.kill()

	# a thread that listens for new Tor61 connection
	# registers this own router
	# when a new Tor61 connection comes in, spawn a new thread to process and create a new Tor61 connection
	def tor61Listener(self):
		print 'tor61Listener'
		new_connection_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		host = socket.gethostname()

		new_connection_listener.bind((host, int(self.port_listening_tor61)))
		new_connection_listener.listen(5)
		
		router_instance_name = 'Tor61Router-' + str(self.group_number) + '-' + str(self.router_instance_number)
		self.registrationUtil = Popen(['python', 'registrationUtility/registration_client.py', str(self.port_listening_tor61), router_instance_name, str(self.agent_id)])

		while self.state == TorRouter.State.running:
			(clientsocket, partneraddress) = new_connection_listener.accept()
			print "Accepting new connection from: " + str(clientsocket) + " " + str(partneraddress)
			# we now have the new TCP
			# this thread creates new Tor61
			connection_handle_thread = threading.Thread(target=self.handle_tor61connection, args=(clientsocket, partneraddress,))
			connection_handle_thread.setDaemon(True)
			connection_handle_thread.start()

	# creates a new Tor61 connection 
	# blocks and listens for the OPEN cell
	# return OPENED cell
	# starts a reading and a writing thread for this connection
	def handle_tor61connection(self, clientsocket, partneraddress):
		(retval, tor61connection) = self.createTor61Connection(partneraddress, clientsocket, False)
		if (retval < 0):
			print "fail on handle_tor61connection"

	# Constructs a stream to given host ip:port.
	# Takes as a parameter a tuple (host, hostport)
	# Returns tuple (1, stream_obj) if stream construction 
	# was successful.
	# Returns (0, None) otherwise
	def startStream(self, host_address):
		# startStream will send a Relay Begin cell down the circuit, then start
		# a timer. If it does not recieve a response withing (10?) seconds, 
		# it will return 0, and proxy should treat this as an error.
		# If router gets back a Begin Failed, it also returns 0 and proxy treats this as an error.
		# If router gets back a Relay Connected, it sends back a 1
		tor61connection =  self.sourceTor61Connection
		c_id = tor61connection.getSourceOutgoingCircuitId()
		pprint(tor61connection.circuit_id_to_circuit_objs)
		# print "Searching for thing with circuit id ", c_id
 		stream_obj = tor61connection.getCircuitObj(c_id).createStream(c_id)
 		tor61connection.startReadingFromStreamBuffer(stream_obj)
		if not stream_obj:
			return (0, None)
		# print "Found Stream object in startStream"
		stream_obj.lockForConnected()
		body = host_address[0] + ":" + str(host_address[1]) + "\0"
		tor61connection.sendRelay(c_id, stream_obj.streamNum, 0x0000, len(body), TorRouter.RELAY_BEGIN, body)
		stream_obj.waitForConnected(10)
		stream_obj.unlockForConnected()
		if (stream_obj.state != TorStream.State.running):
			return (0, None)

		return (1, stream_obj)

	def addProxy(self, proxy):
		self.proxy = proxy

	# Checks the circuit id of the cell and the socket it comes from,
	# look it up on the table to forward it to the appropiate Tor61 connection
	# host_addr should be a (host, host_port) tuple
	def lookUpRoutingTable(self, host_addr, c_id):
		return self.routing_table.get((host_addr, c_id))

	def forwardToTor61(self, redirect_tor61, cell):
		redirect_tor61.sendRelayCell(cell)

	def handleCreated(self, cell):
		c_id, cell_type, padding = struct.unpack('>HBs', cell)
		self.sourceTor61Connection.getCircuit(c_id).onCreate()
		# this is an error... we should only send create once and get created once... 

	def onTor61Close(self, tor61connection):
		print "Tor61Connection partnering with: ", tor61connection.partner_ip_port, " is now closed. Sending destroy"
		tor61connection.sendDestroy()
		self.removePartnerFromRouterIPTorMap(tor61connection.partner_ip_port)
		# for key in self.routing_table:
		# 	if (key[0] == tor61connection.partner_ip_port):
		# 		print "removing element ", key
		# 		self.removePartnerFromRoutingTable(key[0], key[1])

	def onDestroyCell(self, cell, tor61_partner_ip_port):
		c_id, cell_type = struct.unpack('>HB' + ('x' * 509), cell)
		print "Got onDestroy cell: 	cid ", c_id, " cell_type ", cell_type
		redirect_entry = self.lookUpRoutingTable(tor61_partner_ip_port, c_id)
		tor61connection = self.router_ip_to_tor_objs[tor61_partner_ip_port]

		target_host_addr = None
		new_c_id = None
		if (redirect_entry ):	# forward it to the next
			# print "forwarding this destroy cell"
			(target_host_addr, new_c_id) = redirect_entry
			redirect_tor61 = self.router_ip_to_tor_objs.get(target_host_addr)
		
			new_cell = struct.pack('>HB' + ('x' * 509), new_c_id, cell_type)
			# print "forwarding packet ", new_cell
			self.forwardToTor61(redirect_tor61, new_cell)
			self.removePartnerFromRoutingTable(tor61_partner_ip_port, c_id)
			redirect_tor61.removeCircuit(new_c_id)
			self.removePartnerFromRoutingTable(target_host_addr, new_c_id)
		else:
			# print "this destroy cell ends here (we are the source router)"
			pass
		
		#remove circuit from both ends
		tor61connection.removeCircuit(c_id)

	def consoleLogCell(self, c_id, relay_cmd, stream_id):
		s = ""
		if (relay_cmd == TorRouter.RELAY_BEGIN):
			s = "RELAY_BEGIN"
		elif (relay_cmd == TorRouter.RELAY_DATA):
			s = "RELAY_DATA"
		elif (relay_cmd == TorRouter.RELAY_END):
			s = "RELAY_END"
		elif (relay_cmd == TorRouter.RELAY_CONNECTED):
			s = "RELAY_CONNECTED"
		elif (relay_cmd == TorRouter.RELAY_EXTEND):
			s = "RELAY_EXTEND"
		elif (relay_cmd == TorRouter.RELAY_EXTENDED):
			s = "RELAY_EXTENDED"
		elif (relay_cmd == TorRouter.RELAY_BEGIN_FAILED): 
			s = "RELAY_BEGIN_FAILED"
		elif (relay_cmd == TorRouter.RELAY_EXTEND_FAILED): 
			s = "RELAY_EXTEND_FAILED"
		print "Recieved " + s + "	cid: ", c_id, " sid: ", stream_id

	def handleRelay(self, cell, tor61_partner_ip_port):
		c_id, cell_type, stream_id, zeroes, digest, body_length, relay_cmd, body_padding = struct.unpack('>HBHHIHB%ds' % (498,), cell)
		self.consoleLogCell(c_id, relay_cmd, stream_id)
		if (relay_cmd == TorRouter.RELAY_CONNECTED):
			print "aaaaaaaaaaaaaaaaaaaaaaaaa relay connected"

		body = body_padding[:body_length]
		redirect_entry = self.lookUpRoutingTable(tor61_partner_ip_port, c_id)		
		tor61connection = self.router_ip_to_tor_objs[tor61_partner_ip_port]
		pprint(tor61_partner_ip_port)
		# print c_id
		# pprint(self.router_ip_to_tor_objs)
		# pprint(self.routing_table)
		if (redirect_entry):	# forward it to the next
			if c_id != tor61connection.getSourceOutgoingCircuitId() or relay_cmd != TorRouter.RELAY_EXTENDED :
				(host_addr, new_c_id) = redirect_entry
				redirect_tor61 = self.router_ip_to_tor_objs.get(host_addr)
				# print "---------------forwarding: cid: ", new_c_id
				# print "new_c_id ", new_c_id
				# print "cell_type", cell_type
				# print "stream_id", stream_id
				# print "Zeroes", zeroes
				# print "digest", digest
				# print "body_length", body_length
				# print "relay_cmd", relay_cmd
				# # print "body_padding", body_padding
				# print "----------------------------------"
				new_cell = struct.pack('>HBHHIHB%ds' % (498,), new_c_id, cell_type, stream_id, 
					zeroes, digest, body_length, relay_cmd, body_padding)
				# print "forwarding packet ", new_cell
				self.forwardToTor61(redirect_tor61, new_cell)
				return

		tor61connection = self.router_ip_to_tor_objs.get(tor61_partner_ip_port)
		if (relay_cmd == TorRouter.RELAY_BEGIN):			# for stream 
			stream_obj = tor61connection.getCircuit(c_id).createStream(c_id, stream_id)
			tor61connection.startReadingFromStreamBuffer(stream_obj)
			tcp_host, temp = body.split(':')
			tcp_host_port, host_agent_id = temp.split('\0')
			tcp_host_port = int(tcp_host_port)
			# opens a TCP connection on the proxy side
			retval = self.proxy.connect_to_server((tcp_host, tcp_host_port), stream_obj)	
			if (retval > 0):
				tor61connection.sendRelay(c_id, stream_id, TorRouter.RELAY_DIGEST_CONSTANT, 0, TorRouter.RELAY_CONNECTED, '')
			else:
				tor61connection.sendRelay(c_id, stream_id, TorRouter.RELAY_DIGEST_CONSTANT, 0, TorRouter.RELAY_BEGIN_FAILED, '')

		elif (relay_cmd == TorRouter.RELAY_DATA):			# for stream
			stream_obj = tor61connection.getCircuit(c_id).getStream(stream_id)
			retval= stream_obj.sendAllToProxy(body)
			if (retval < 0):
				print "stream_obj is dead"

		elif (relay_cmd == TorRouter.RELAY_END):			# for stream
			stream_obj = tor61connection.getCircuit(c_id).getStream(stream_id)
			stream_obj.closeStream()

		elif (relay_cmd == TorRouter.RELAY_CONNECTED):	# for stream
			stream_obj = tor61connection.getCircuit(c_id).getStream(stream_id)
			stream_obj.notifyConnected()

		elif (relay_cmd == TorRouter.RELAY_EXTEND):		# for circuit, create new outgoing circuit
			target_ip_port, opened_agent_id = struct.unpack('>%dsI' % (len(body) - 4,), body)
			tcp_host, tcp_host_port = target_ip_port.split(':')
			tcp_host_port = tcp_host_port[:len(tcp_host_port) - 1] # drop the null byte
			print "==============================", tcp_host_port
			tcp_host_port = int(tcp_host_port)
			tor61 = self.findTor61Connection((tcp_host, tcp_host_port))
			circuit_obj = None
			if tor61 is None:
				socket = TorRouter.createTCPConnection((tcp_host, tcp_host_port))
				print " trying connecting to the next hop router "
				if socket is None:	# TCP connection failed
					tor61connection.sendRelay(c_id, stream_id, digest, body_length, TorRouter.RELAY_EXTEND_FAILED, body_padding)
				(retval, tor61) = self.createTor61Connection((tcp_host, tcp_host_port), socket, True, opener_agent_id=self.agent_id, opened_agent_id=opened_agent_id)

			self.addPartnerToRouterIPTorMap((tcp_host, tcp_host_port), tor61)
			retval, circuit_obj = tor61.sendCreate(False)
			if (retval < 0):
				"print sendCreate error"

			# above blocks until we have received created
			if (circuit_obj): 
				# wait for the second relay extend
				circuit_obj.receive_relayextend_condition.acquire()
				tor61connection.sendRelay(c_id, stream_id, digest, 0, TorRouter.RELAY_EXTENDED, '')
				circuit_obj.receive_relayextend_condition.wait(10)
				circuit_obj.receive_relayextend_condition.release()
				print "putting INTO the routing table"
				self.addPartnerToRoutingTable((tor61_partner_ip_port, c_id),(tor61.partner_ip_port, circuit_obj.getCid()))
				self.addPartnerToRoutingTable((tor61.partner_ip_port, circuit_obj.getCid()), (tor61_partner_ip_port, c_id))
				# pprint(self.routing_table)
			else:
				pass
			# else : (got CREATE FAILED) do nothing?? 

		elif (relay_cmd == TorRouter.RELAY_EXTENDED):		# for circuit
			tor61 = self.findTor61Connection(tor61_partner_ip_port)
			source_c_id = tor61.getSourceOutgoingCircuitId()
			# if (source_c_id != c_id):
			# 	print "Getting a TorRouter.RELAY EXTENDED should be meant for itself, but wrong c_id", source_c_id, " | ", c_id
			# 	return
			circuit_obj = self.sourceTor61Connection.getCircuit(c_id)
			circuit_obj.receive_relayextend_condition.acquire()
			circuit_obj.onRelayExtended()
			circuit_obj.receive_relayextend_condition.success = 1
			circuit_obj.receive_relayextend_condition.notify(10)
			circuit_obj.receive_relayextend_condition.release()

		elif (relay_cmd == TorRouter.RELAY_BEGIN_FAILED):	# for stream
			stream_obj = tor61connection.getCircuit(c_id).getStream(stream_id)
			stream_obj.notifyFailed()

		elif (relay_cmd == TorRouter.RELAY_EXTEND_FAILED):	# for stream
			circuit_obj = self.sourceTor61Connection.getCircuit(c_id)
			circuit_obj.receive_relayextend_condition.acquire()
			circuit_obj.receive_relayextend_condition.notify(10)
			circuit_obj.receive_relayextend_condition.success = 0
			circuit_obj.receive_relayextend_condition.release()

		else:		
			print "error. no such Relay cell type"

	# return this tor connection if exists, otherwise None
	def findTor61Connection(self, partner_host_address):
		try: 
			return self.router_ip_to_tor_objs[partner_host_address]
		except KeyError as e:
			return None

	@staticmethod
	def createTCPConnection(partner_host_addr):
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		retval = s.connect_ex(partner_host_addr)
		if (retval != 0):
			print "TCP connection failedddd to ", partner_host_addr
			return None
		return s

	# partner_host_addr = (host, port)
	def createTor61Connection(self, partner_host_addr, socket, we_are_initiator, **kwargs):
		# establish Tor61 connection for the circuit from source router
		tor61connection = Tor61Connection(partner_host_addr, socket, we_are_initiator)
		tor61connection.addOnRelayHandler(self.handleRelay)
		tor61connection.addOnDestroyHandler(self.onDestroyCell)
		tor61connection.addOnSocketCloseHandler(self.onTor61Close)
		if (we_are_initiator):
			retval = tor61connection.startAsOpener(kwargs['opener_agent_id'], kwargs['opened_agent_id'])
		else:
			retval = tor61connection.startAsOpened() 	# blocking call. waiting for open
		if (retval > 0):
			self.router_ip_to_tor_objs[partner_host_addr] = tor61connection
			# loop the above until this successes...(but do we listen for tor61 is not sucess??)


		return (retval, tor61connection)


