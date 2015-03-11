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
		self.port_listening_tor61 = sys.argv[3]			# which port should we be listening
		self.agent_id = (int(self.group_number) << 16) | int(self.router_instance_number)

		self.next_socket_num = 1
		self.next_socket_num_lock = threading.Lock()

		# def relayExtendListener(ip, port):
		# 	#perform relay extend

		# x.addRelayExtendListener(relayExtendListener)

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
		# fork + exec to contact registration service
		connect_handle_thread = threading.Thread(target=self.tor61Listener)
		connect_handle_thread.setDaemon(True)
		connect_handle_thread.start()

		retval = -1
		tor61connection = None
		while (retval < 0):	
			try: 
				# TODO: Get list of possible hosts from registration
				# service, pick one at random as partner_host_addr
				print "trying to get a list of possible Tor routers......"
				p = Popen(['python', 'registrationUtility/fetch.py', 'Tor61Router-' + str(self.group_number)], stdin=PIPE, stdout=PIPE, stderr=PIPE)
				output, err = p.communicate() # lol error
				print err
				# output = "128.208.1.179	3333	474612712\n"
				print output
				lines = output.split('\n')
				# if (len(lines) < 4):
				# 	#print 'not enough routers available ' + str(len(lines))
				# 	#print lines[0]
				# 	continue
				retval = -1
				if (len(lines) > 1):
					rand = random.randint(0, len(lines) - 2)
					line = lines[rand].split('\t')
					partner_host_addr = (line[0], int(line[1]))
					print "Attempting to connect TCP to :" + str(partner_host_addr)
					# establish TCP 
					socket = TorRouter.createTCPConnection(partner_host_addr)

					(retval, tor61connection) = self.createTor61Connection( partner_host_addr, socket, True, 
																			opener_agent_id=self.agent_id, opened_agent_id=line[2])
			except IndexError:
				self.killRouter()

		# 	build our first tor61connection
		self.sourceTor61Connection = tor61connection

		#	Create circuit -- this blocks until response or timeout
		self.router_ip_to_tor_objs[partner_host_addr] = tor61connection
		retval, circuit_obj = self.sourceTor61Connection.sendCreate(True)
		# self.routing_table[(partner_host_addr, circuit_obj.getCid())] = None
		if(retval != 1):
			print "Error -- sendCreate did not succeed. Error code: ", retval
			return -1

		print "Create suceeded."

		for i in range (1, 3):
			print "Beginning iteration ", i ," of loop."
			print 'circuit_obj.state ' + str(circuit_obj.state)
			rand = random.randint(0, len(lines) - 2)
			line = lines[rand].split('\t')
			secondHopAddr = (line[0], line[1]) # "ip:por0<agentid>", get from registration
			body_message = line[0] + ":" + line[1] + '\0' + line[2]
			print "body message: " + body_message + " LENGTH OF BODY MESSAGE IS " + str(len(body_message))
			circuit_obj.receive_relayextend_condition.acquire()
			circuit_obj.receive_relayextend_condition.success = 0
			retval = self.sourceTor61Connection.sendRelay(circuit_obj.getCid(), TorStream.STREAM_ZERO_RELAY_EXTEND, 
				TorRouter.RELAY_DIGEST_CONSTANT, len(body_message), TorRouter.RELAY_EXTEND, body_message) # 	def sendRelay(self, c_id, stream_id, digest, relay_cmd, body):
			circuit_obj.receive_relayextend_condition.wait(10)
			circuit_obj.receive_relayextend_condition.release()

			if(circuit_obj.receive_relayextend_condition.success == 0):
				return -1

		# line = lines[2].split(' ')
		# thirdHopAddr  (line[0], line[1])# "ip:por0<agentid>", get from registration
		# body_message = stline[0] + ":" + line[1] + "\0" + line[2]
		# circuit_obj.receive_relayextend_condition.acquire()
		# retval = self.sourceTor61Connection.sendRelay(circuit_obj.getCid(), TorStream.STREAM_ZERO_RELAY_EXTEND, 
		# 	RELAY_DIGEST_CONSTANT, len(thirdHopAddr), RELAY_EXTEND, body_message) # 	def sendRelay(self, c_id, stream_id, digest, relay_cmd, body):
		# circuit_obj.receive_relayextend_condition.wait(10)
		# circuit_obj.receive_relayextend_condition.release()

		if (circuit_obj.state == Circuit.State.three_hop):
			print 'building circuit done'
			return 1

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
		# message_log("Router listening on " + socket.gethostbyname(socket.gethostname()) + ":" + port_listening)
		# register ourselves
		
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
		print "Searching for thing with circuit id ", c_id
 		stream_obj = tor61connection.getCircuitObj(c_id).createStream(c_id)
 		tor61connection.startReadingFromStreamBuffer(stream_obj)
		if not stream_obj:
			return (0, None)
		print "Found Stream object in startStream"
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
		# TODO change the c_id, repack the cell 
		redirect_tor61.sendRelayCell(cell)

	def handleCreated(self, cell):
		c_id, cell_type, padding = struct.unpack('>HBs', cell)
		self.sourceTor61Connection.getCircuit(c_id).onCreate()
		# this is an error... we should only send create once and get created once... 

	def onDestroyCell(self, cell, tor61_partner_ip_port):
		# 
		c_id, cell_type = struct.unpack('>HB' + ('x' * 509), cell)

		redirect_entry = self.lookUpRoutingTable(tor61_partner_ip_port, c_id)

		target_host_addr = None
		new_c_id = None
		if (redirect_entry ):	# forward it to the next
			(target_host_addr, new_c_id) = redirect_entry
			redirect_tor61 = self.router_ip_to_tor_objs.get(target_host_addr)
		
			new_cell = struct.pack('>HB' + ('x' * 509), new_c_id, cell_type)
			# print "forwarding packet ", new_cell
			self.forwardToTor61(redirect_tor61, new_cell)
			
		tor61connection = self.router_ip_to_tor_objs[tor61_partner_ip_port]
		
		#remove circuit from both ends

		tor61connection.removeCircuit(c_id)

		self.routing_table.pop((tor61_partner_ip_port, c_id))
		if(target_host_addr):
			redirect_tor61.removeCircuit(new_c_id)
			self.routing_table.pop((target_host_addr, new_c_id))



	def handleRelay(self, cell, tor61_partner_ip_port):

		c_id, cell_type, stream_id, zeroes, digest, body_length, relay_cmd, body_padding = struct.unpack('>HBHHIHB%ds' % (498,), cell)
		print "RELAY TYPE ", relay_cmd

		body = body_padding[:body_length]
		redirect_entry = self.lookUpRoutingTable(tor61_partner_ip_port, c_id)		
		tor61connection = self.router_ip_to_tor_objs[tor61_partner_ip_port]
		pprint(tor61_partner_ip_port)
		# print c_id
		# pprint(self.router_ip_to_tor_objs)
		# pprint(self.routing_table)
		if (redirect_entry ):	# forward it to the next
			if c_id != tor61connection.getSourceOutgoingCircuitId() or relay_cmd != TorRouter.RELAY_EXTENDED :
				# tor61_partner_ip_port
				# router_ip_to_tor_objs
			
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
			# create a stream
			print "Recieved RELAY_BEGIN, cid: ", c_id, " stream_id: ", stream_id
			pprint(tor61connection.circuit_id_to_circuit_objs)
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
			print "Recieved RELAY_DATA, cid: ", c_id, " stream_id: ", stream_id

			stream_obj = tor61connection.getCircuit(c_id).getStream(stream_id)
			retval= stream_obj.sendAllToProxy(body)
			if (retval < 0):
				print "stream_obj is dead"

		elif (relay_cmd == TorRouter.RELAY_END):			# for stream
			print "Recieved RELAY_END, cid: ", c_id, " stream_id: ", stream_id

			stream_obj = tor61connection.getCircuit(c_id).getStream(stream_id)
			stream_obj.closeStream()

		elif (relay_cmd == TorRouter.RELAY_CONNECTED):	# for stream
			print "Recieved RELAY_CONNECTED, cid: ", c_id, " stream_id: ", stream_id

			stream_obj = tor61connection.getCircuit(c_id).getStream(stream_id)
			stream_obj.notifyConnected()

		elif (relay_cmd == TorRouter.RELAY_EXTEND):		# for circuit, create new outgoing circuit
			print "Recieved RELAY_EXTEND, cid: ", c_id, " stream_id: ", stream_id

			tcp_host, temp = body.split(':')
			tcp_host_port, opened_agent_id = temp.split('\0')
			tcp_host_port = int(tcp_host_port)
			tor61 = self.findTor61Connection((tcp_host, tcp_host_port))
			circuit_obj = None
			print "!!!!! [handleRelay] Circuit ID from sender is ", c_id,
			if (tor61):
				self.router_ip_to_tor_objs[(tcp_host, tcp_host_port)] = tor61
				retval, circuit_obj = tor61.sendCreate(False)

				print "!!!!! [handleRelay] Circuit ID to destination is ", circuit_obj.getCid(),

				self.routing_table[(tor61_partner_ip_port, c_id)] = (tor61.partner_ip_port, circuit_obj.getCid())
				self.routing_table[(tor61.partner_ip_port, circuit_obj.getCid())] = (tor61_partner_ip_port, c_id)
			else: 
				# THERES BUGS HERE
				socket = TorRouter.createTCPConnection((tcp_host, tcp_host_port))
				(retval, tor61) = self.createTor61Connection((tcp_host, tcp_host_port), socket, True, opener_agent_id=self.agent_id, opened_agent_id=opened_agent_id)

				self.router_ip_to_tor_objs[(tcp_host, tcp_host_port)] = tor61
				retval, circuit_obj = tor61.sendCreate(False)

				print "!!!!! [handleRelay ELSE] Circuit ID to destination is ", circuit_obj.getCid(),

				self.routing_table[(tor61_partner_ip_port, c_id)] = (tor61.partner_ip_port, circuit_obj.getCid())
				self.routing_table[(tor61.partner_ip_port, circuit_obj.getCid())] = (tor61_partner_ip_port, c_id)



			# above blocks until we have received created
			if (circuit_obj): 
				circuit_obj.receive_relayextend_condition.acquire()
				# c_id, stream_id, digest, relay_cmd, body
				tor61connection.sendRelay(c_id, stream_id, digest, 0, TorRouter.RELAY_EXTENDED, '')
				circuit_obj.receive_relayextend_condition.wait(10)
				circuit_obj.receive_relayextend_condition.release()

			# else : (got CREATE FAILED) do nothing?? 

		elif (relay_cmd == TorRouter.RELAY_EXTENDED):		# for circuit
			print "Recieved RELAY_EXTENDED, cid: ", c_id, " stream_id: ", stream_id
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
			print "Recieved RELAY_BEGIN_FAILED, cid: ", c_id, " stream_id: ", stream_id

			stream_obj = tor61connection.getCircuit(c_id).getStream(stream_id)
			stream_obj.notifyFailed()
		elif (relay_cmd == TorRouter.RELAY_EXTEND_FAILED):	# for stream
			print "Recieved RELAY_EXTEND_FAILED, cid: ", c_id, " stream_id: ", stream_id

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
		s.connect(partner_host_addr)
		return s

	# partner_host_addr = (host, port)
	def createTor61Connection(self, partner_host_addr, socket, we_are_initiator, **kwargs):
		# establish Tor61 connection for the circuit from source router
		tor61connection = Tor61Connection(partner_host_addr, socket, we_are_initiator)
		tor61connection.addOnRelayHandler(self.handleRelay)
		tor61connection.addOnDestroyHandler(self.onDestroyCell)
		if (we_are_initiator):
			retval = tor61connection.startAsOpener(kwargs['opener_agent_id'], kwargs['opened_agent_id'])
		else:
			retval = tor61connection.startAsOpened() 	# blocking call. waiting for open
		if (retval > 0):
			self.router_ip_to_tor_objs[partner_host_addr] = tor61connection
			# loop the above until this successes...(but do we listen for tor61 is not sucess??)


		return (retval, tor61connection)


