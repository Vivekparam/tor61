# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015
import struct
import threading
from Queue import Queue
from circuit import Circuit

class Tor61Connection(object):
	class State(object):
		init = 0
		opened = 1
		failed = 3
	
	ZERO_CIRCUIT = 0x0000

	# ***** CELL TYPES ***** #
	CELL_TYPE_OPEN = 0x05
	CELL_TYPE_OPENED = 0x06
	CELL_TYPE_OPEN_FAILED = 0x07
	CELL_TYPE_CREATE = 0x01
	CELL_TYPE_CREATED = 0x02
	CELL_TYPE_CREATE_FAILED = 0x08
	CELL_TYPE_DESTROY = 0x04
	CELL_TYPE_RELAY = 0x03

	# ***** CELL PADDING CONSTANTS *****#
	PADDING_OPEN = 501
	PADDING_CREATE = 509
	PADDING_RELAY = 512 - 2 -1 -2 -2 - 4 - 2 - 1


	def __init__(self, partner_ip_port, socket, we_are_initiator):
		self.state = Tor61Connection.State.init
		self.circuit_id_to_circuit_objs = {}
		self.we_are_initiator = we_are_initiator
		print "PARTNER IP PORT ", partner_ip_port 
		self.partner_ip_port = partner_ip_port
		self.source_outgoing_c_id = 1
		self.next_circuit_num_lock = threading.Lock()

		# This is the socket through which
		# the two routers will communicate
		self.socket = socket

		# We only put packaged cells into this queue
		self.socket_buffer = Queue()
		self.opened_condition = threading.Condition()
		self.open_condition = threading.Condition()

	# Open starts this tor61 connection.
	# Sends an OPEN cell to the other end
	# of the associated socket.
	# Returns 1 if open operation was successful
	# Returns -1 if got OPEN_FAILED
	# returns -2 if no response
	def startAsOpener(self, opener_agent_id, opened_agent_id):
		self.opener_agent_id = opener_agent_id
		self.opened_agent_id = opened_agent_id
		if not self.we_are_initiator:
			print "startAsOpener should only be called if we initiated the connection."
			return -1

		cell = None
		self.next_circuit_num = 3
		# we need to send an open, then wait for resp
		self.opened_condition.acquire()
		self.startReaderWriter()
		self.send(Tor61Connection.ZERO_CIRCUIT, Tor61Connection.CELL_TYPE_OPEN, opener_agent_id=self.opener_agent_id, opened_agent_id=self.opened_agent_id)
		
		# Wait for either OPENED or OPEN_FAILED response
		self.opened_condition.wait(10) # secs
		self.opened_condition.release()
		
		# cell_type = self.opened_condition.cell_type

		if (self.state == Tor61Connection.State.opened):
			return 1
		elif (self.state == Tor61Connection.State.failed):	
			print "received CELL_TYPE_OPEN_FAILED!"
			return -1
		else:	# self.state == State.init
			print "Did not get a response for OPEN within timeout."
			return -2

	def sendCreate(self, we_are_source):
		circuit_obj = None
		c_id = None
		if (we_are_source):
			print "We are source in sendCreate."
			c_id = self.source_outgoing_c_id
			print "Creating circuit with c_id " + str(c_id)
			circuit_obj = Circuit(c_id)

			# Get list of routers we can use
			# select one at random
		else:
			# print "We are not source in sendCreate. Grabbing lock for circuitnum."
			# In this case, we might be asked to extend by someone else to a destination
			# to whom the other end was the source of the TCP connection
			self.next_circuit_num_lock.acquire()
			circuit_obj = Circuit(self.next_circuit_num)
			c_id = self.next_circuit_num
			self.next_circuit_num += 2
			self.next_circuit_num_lock.release()
			
		self.circuit_id_to_circuit_objs[c_id] = circuit_obj
		# send create & wait for CREATE CREATE_FAILED
		circuit_obj.receive_created_condition.acquire()
		circuit_obj.receive_created_condition.success = 0
		self.send(c_id, Tor61Connection.CELL_TYPE_CREATE)
		circuit_obj.receive_created_condition.wait(10)
		circuit_obj.receive_created_condition.release()

		if (circuit_obj.receive_created_condition.success == 1):
			print 'send create success'
			circuit_obj.onCreated()
		else: 
			return (0, None)
			print 'send CREATE failed'
			# try another router
			# select another router at random

		# circuit is ready
		return (1, circuit_obj)

	# Q: do we know the opener_agent_id, opened_agent_id before getting the OPEN?
	def startAsOpened(self):
		if(self.we_are_initiator):
			print "startAsOpened should only be called if we did not initiate the connection."
			return -1
		# we are not the initiator
		self.next_circuit_num = 2

		# Wait for either OPEN 
		self.open_condition.acquire()
		self.startReaderWriter()	# reader -> handle cell notifies 
		self.open_condition.wait(10) # timeout in secs
		self.open_condition.release()

		if (self.state == Tor61Connection.State.opened):
			return 1
		else: # self.state == State.init
			print "Did not get a response for OPEN within timeout."
			return -2

	def socket_writer(self):
		while(True):
			data = self.socket_buffer.get(True)
			# print "Sending data: " + data + " of length " + str(len(data))

			self.socket.sendall(data)

	def socket_reader(self):
		while (True):
			length_received = 0
			cell = ""
			while (length_received < 512):
				data = self.socket.recv(512 - length_received)
				length_received += len(data)
				# print "Got data: " + data + " (Length so far is: " + str(length_received) + ")"
				if not (data):
					print "no more received data"
					# on error
					break
				else:
					cell += data
			# spawn handle-cell thread
			print "Calling handleCell with data: " + cell + " of length " + str(len(cell))
			connect_handle_thread = threading.Thread(target=self.handleCell, args=(cell,))
			connect_handle_thread.setDaemon(True)
			connect_handle_thread.start()
			# self.handleCell(cell)

	def startReaderWriter(self):
		# Spawn socket writing thread
		connect_handle_thread = threading.Thread(target=self.socket_writer)
		connect_handle_thread.setDaemon(True)
		connect_handle_thread.start()

		# spawn socket reader thread
		connect_handle_thread = threading.Thread(target=self.socket_reader)
		connect_handle_thread.setDaemon(True)
		connect_handle_thread.start()
		# put an entry into circuit_id_to_circuit_objs

	def handleCell(self, cell):
		c_id, cell_type = struct.unpack('>HB' + ('x' * 509), cell)
		print "MESSAGE FROM ", self.partner_ip_port, " with cid: ", str(c_id)
		if(cell_type == Tor61Connection.CELL_TYPE_OPENED):
			# self.opened_condition.cell_type = CELL_TYPE_OPENED
			print "***** HANDLE_CELL ***** CELL_TYPE_OPENED on circuit " + str(c_id)

			self.opened_condition.acquire()
			self.opened_condition.notify()
			self.opened_condition.release()

			# self.onOpened()
			self.state = Tor61Connection.State.opened 
		elif(cell_type == Tor61Connection.CELL_TYPE_OPEN):
			print "***** HANDLE_CELL ***** CELL_TYPE_OPEN on circuit " + str(c_id)

			# should be the first cell received on this new Tor61 if self.we_are_initiator == False
			self.open_condition.acquire()
			self.open_condition.notify()
			self.open_condition.release()

			c_id, cell_type, opener_agent_id, opened_agent_id = struct.unpack('>HBII' + ('x' * 501), cell)

			self.opener_agent_id = opener_agent_id
			self.opened_agent_id = opened_agent_id
			# need to send a opened
			self.send(Tor61Connection.ZERO_CIRCUIT, Tor61Connection.CELL_TYPE_OPENED, opener_agent_id=opener_agent_id, opened_agent_id=opened_agent_id)
			self.state = Tor61Connection.State.opened

		elif(cell_type == Tor61Connection.CELL_TYPE_RELAY):
			print "***** HANDLE_CELL ***** CELL_TYPE_RELAY on circuit " + str(c_id)

			self.onRelay(cell, self.partner_ip_port)

		elif(cell_type == Tor61Connection.CELL_TYPE_DESTROY):
			print "***** HANDLE_CELL ***** CELL_TYPE_DESTROY on circuit " + str(c_id)

			self.onDestroy(cell)

		elif(cell_type == Tor61Connection.CELL_TYPE_CREATE):
			print "***** HANDLE_CELL ***** CELL_TYPE_CREATE on circuit " + str(c_id)

			self.send(c_id, Tor61Connection.CELL_TYPE_CREATED)
			self.circuit_id_to_circuit_objs[c_id] = Circuit(c_id)
			# self.onCreate(cell)

		elif(cell_type == Tor61Connection.CELL_TYPE_CREATED):
			print "***** HANDLE_CELL ***** CELL_TYPE_CREATED on circuit " + str(c_id)

			circuit_obj = self.circuit_id_to_circuit_objs[c_id]
			circuit_obj.receive_created_condition.acquire()
			circuit_obj.receive_created_condition.notify()
			circuit_obj.receive_created_condition.success = 1
			circuit_obj.receive_created_condition.release()

		elif(cell_type == Tor61Connection.CELL_TYPE_OPEN_FAILED):
			print "***** HANDLE_CELL ***** CELL_TYPE_OPEN_FAILED on circuit " + str(c_id)

			self.opened_condition.cell_type = Tor61Connection.CELL_TYPE_OPEN_FAILED
			self.opened_condition.notify()
			self.onOpenFailed(cell)

		elif(cell_type == Tor61Connection.CELL_TYPE_CREATE_FAILED):
			print "***** HANDLE_CELL ***** CELL_TYPE_CREATE_FAILED on circuit " + str(c_id)

			circuit_obj = self.circuit_id_to_circuit_objs[c_id]
			circuit_obj.receive_created_condition.acquire()
			circuit_obj.receive_created_condition.notify()
			circuit_obj.receive_created_condition.success = 0
			circuit_obj.receive_created_condition.release()
		else:
			print "UNKOWN CELL TYPE ", cell_type

	def getCircuitObj(self, c_id):
		return self.circuit_id_to_circuit_objs[c_id]

	def forward(self, c_id, cell):
		 new_cell = struct.pack_into('>H', cell, 0, c_id)

	# callbacks
	# def addOpenListener(self, callback):
	# 	self.onOpen = callback

	def addOnCreateListener(self, callback):
		self.onCreate = callback

	def addOnRelayHandler(self, callback):
		self.onRelay = callback

	# Define all send functions
	def send(self, c_id, cell_type, **kwargs):
		print "@@@@ SEND @@@@ sending " + str(cell_type) + " on circuit " + str(c_id)
		if (cell_type == Tor61Connection.CELL_TYPE_OPEN) or \
			(cell_type == Tor61Connection.CELL_TYPE_OPENED) or \
			(cell_type == Tor61Connection.CELL_TYPE_OPEN_FAILED):	
			cell = struct.pack('>HBII' + ('x' * Tor61Connection.PADDING_OPEN), c_id, cell_type, int(kwargs['opener_agent_id']), int(kwargs['opened_agent_id']))
		elif (cell_type == Tor61Connection.CELL_TYPE_CREATE) or \
			(cell_type == Tor61Connection.CELL_TYPE_CREATED) or \
			(cell_type == Tor61Connection.CELL_TYPE_DESTROY) or \
			(cell_type == Tor61Connection.CELL_TYPE_CREATE_FAILED): 
			# padding = bytearray(Tor61Connection.PADDING_CREATE)
			cell = struct.pack('>HB' + ('x' * Tor61Connection.PADDING_CREATE), c_id, cell_type)
		elif cell_type == Tor61Connection.CELL_TYPE_RELAY: 
			print "\t\tRELAY TYPE: " + str(kwargs['relay_cmd'])
			digest = int(kwargs['digest'])
			zeroes = 0x0000
			# print 'padding length of ' + str(Tor61Connection.PADDING_RELAY - kwargs['body_length'])
			# print 'body length of ' + str(len( kwargs['body']))
			body_len = len( kwargs['body'])
			body = bytes(kwargs['body'])
			cell = struct.pack('>HBHHIHB%ds' % (body_len,) + ('x' * (Tor61Connection.PADDING_RELAY - body_len)) , c_id, cell_type, kwargs['stream_id'], 
				zeroes, digest, kwargs['body_length'], kwargs['relay_cmd'], body)
			# print 'sending cell length of: ' + str(len(cell))
		else:
			print "UNKNOWN CELL TYPE " , cell_type 
			return -1
		self.socket_buffer.put(cell)

	def getCircuit(self, c_id):
		return self.circuit_id_to_circuit_objs.get(c_id)

	# for router
	def sendRelay(self, c_id, stream_id, digest, body_length, relay_cmd, body):
		self.send(c_id, Tor61Connection.CELL_TYPE_RELAY, stream_id=stream_id, digest=digest, body_length=body_length, relay_cmd=relay_cmd, body=body)

	def sendRelayCell(self, cell):
		self.socket_buffer.put(cell)

	def getSourceOutgoingCircuitId(self):
		return self.source_outgoing_c_id

	def startReadingFromStreamBuffer(self, stream_obj):
		# Spawn socket writing thread
		connect_handle_thread = threading.Thread(target=self.stream_buffer_reader, args=(stream_obj,))
		connect_handle_thread.setDaemon(True)
		connect_handle_thread.start()

	def stream_buffer_reader(self, stream_obj):
		while(True):
			print "WAITING FOR NEXT ELEMENT FROM PROXY"
			data = stream_obj.getNextFromProxy()
			self.socket_buffer.put(data)
