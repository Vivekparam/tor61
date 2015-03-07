# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015
import struct
import threading
from enum import Enum

class Tor61Connection(object):
	State = enum(init=0, opened=1, stopped=2, failed=3) 
	
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
	PADDING_RELAY = 498


	def __init__(self, partner_ip_port, socket, we_are_initiator):
		self.circuit_id_to_circuit_objs = {}
		self.we_are_initiator = we_are_initiator
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
		if(!we_are_initiator):
			print "startAsOpener should only be called if we initiated the connection."
			return -1

		cell = None
		self.next_circuit_num = 3
		# we need to send an open, then wait for resp
		self.opened_condition.acquire()
		send(ZERO_CIRCUIT, CELL_TYPE_OPEN, opener_agent_id=self.opener_agent_id, opened_agent_id=self.opened_agent_id)
		
		# Wait for either OPENED or OPEN_FAILED response
		self.opened_condition.wait(10) # secs
		self.opened_condition.release()
		
		# cell_type = self.opened_condition.cell_type

		if (self.state == State.opened):
			startReaderWriter() # need to first wait, then read from the reading thread
			return 1
		elif (self.state == State.failed):	
			print "received CELL_TYPE_OPEN_FAILED!"
			return -1
		else	# self.state == State.init
			print "Did not get a response for OPEN within timeout."
			return -2

	def sendCreate(we_are_source):
		if (we_are_source):
			c_id = self.source_outgoing_c_id
			circuit_obj = Circuit(c_id)
			self.circuit_id_to_circuit_objs[c_id] = circuit_obj

			# Get list of routers we can use
			# select one at random
		else:
			# In this case, we might be asked to extend by someone else to a destination
			# to whom the other end was the source of the TCP connection
			self.next_circuit_num_lock.acquire()
			circuit_obj = Circuit(self.next_circuit_num)

			self.circuit_id_to_circuit_objs[self.next_circuit_num] = circuit_obj
			self.next_circuit_num += 2
			self.next_circuit_num_lock.release()
			
		# send create & wait for CREATE CREATE_FAILED
		circuit_obj.receive_created_condition.acquire()
		send(c_id, CELL_TYPE_CREATE)
		circuit_obj.receive_created_condition.wait(10)
		circuit_obj.receive_created_condition.release()

		if (circuit_obj.receive_created_condition.success):
			print 'send create success'
		else: 
			return (0, None)
			print 'send CREATE failed'
			# try another router
			# select another router at random

		# circuit is ready
		return (1, circuit_obj)

	# Q: do we know the opener_agent_id, opened_agent_id before getting the OPEN?
	def startAsOpened(self):
		if(we_are_initiator):
			print "startAsOpened should only be called if we did not initiate the connection."
			return -1
		# we are not the initiator
		self.next_circuit_num = 2

		# Wait for either OPEN 
		self.open_condition.acquire()
		startReaderWriter()	# reader -> handle cell notifies 
		self.open_condition.wait(10) # timeout in secs
		self.open_condition.release()

		if (self.state == State.opened):
			return 1
		else	# self.state == State.init
			print "Did not get a response for OPEN within timeout."
			return -2

	def socket_writer(self):
		data = self.socket_buffer.get(True)
		self.socket.sendAll(data);

	def socket_reader(self):
		length_received = 0
		cell = ""
		while (length_received < 512)
			data = self.socket.recv(512 - length_received)
			if not (data):
				print "no more received data"
				# on error
				break
			else:
				cell += data
		# spawn handle-cell thread
		connect_handle_thread = threading.Thread(target=self.handleCell, args=(cell,))
		connect_handle_thread.setDaemon(True)
		connect_handle_thread.start()handleCell(cell)

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

	def handleCell(cell):
		c_id, cell_type, other = struct.unpack('>HBs', cell)
		if(cell_type == CELL_TYPE_OPENED):
			print "This is really weird we shouldnt be here -- CELL_TYPE_OPENED"
			# self.opened_condition.cell_type = CELL_TYPE_OPENED

			self.opened_condition.acquire()
			self.opened_condition.notify()
			self.opened_condition.release()

			# self.onOpened()
			self.state = State.opened 
		elif(cell_type == CELL_TYPE_OPEN):
			# should be the first cell received on this new Tor61 if self.we_are_initiator == False
			self.open_condition.acquire()
			self.open_condition.notify()
			self.open_condition.release()

			# cast to unsigned int
			opener_agent_id = struct.pack('>I', other[:4])
			opened_agent_id = struct.pack('>I', other[4:8])
			self.opener_agent_id = opener_agent_id
			self.opened_agent_id = opened_agent_id
			# need to send a opened
			send(ZERO_CIRCUIT, CELL_TYPE_OPENED, opener_agent_id=opener_agent_id, opened_agent_id=opened_agent_id)
			self.state = State.opened

		elif(cell_type == CELL_TYPE_RELAY):
			self.onRelay(cell, self.partner_ip_port)

		elif(cell_type == CELL_TYPE_DESTROY):
			self.onDestroy(cell)

		elif(cell_type == CELL_TYPE_CREATE):
			send(c_id, CELL_TYPE_CREATED)
			self.onCreate(cell)

		elif(cell_type == CELL_TYPE_CREATED):
			circuit_obj = self.circuit_id_to_circuit_objs[c_id]
			circuit_obj.receive_created_condition.acquire()
			circuit_obj.receive_created_condition.notify()
			circuit_obj.receive_created_condition.success = 1
			circuit_obj.receive_created_condition.release()

		elif(cell_type == CELL_TYPE_OPEN_FAILED):
			self.opened_condition.cell_type = CELL_TYPE_OPEN_FAILED
			self.opened_condition.notify()
			self.onOpenFailed(cell)

		else(cell_type == CELL_TYPE_CREATE_FAILED):
			circuit_obj = self.circuit_id_to_circuit_objs[c_id]
			circuit_obj.receive_created_condition.acquire()
			circuit_obj.receive_created_condition.notify()
			circuit_obj.receive_created_condition.success = 0
			circuit_obj.receive_created_condition.release()

	def getCircuitObj(self, c_id):
		return self.circuit_id_to_circuit_objs[c_id]

	def forward(self, c_id, cell):
		 new_cell = struct.pack_into('>H', cell, 0, c_id)

	# callbacks
	# def addOpenListener(self, callback):
	# 	self.onOpen = callback

	def addOnCreateListener(callback):
		self.onCreate = callback

	def addOnRelayHandler(self, callback):
		self.onRelayBegin = callback

	# Define all send functions
	def send(self, c_id, cell_type, **kwargs):
		if (cell_type == CELL_TYPE_OPEN) or \
			(cell_type == CELL_TYPE_OPENED) or \
			(cell_type == CELL_TYPE_OPEN_FAILED):	
			padding = char[PADDING_OPEN]
			cell = struct.pack('>HBIIs', c_id, cell_type, kwargs['opener_agent_id'], kwargs['opened_agent_id'], padding)
		elif (cell_type == CELL_TYPE_CREATE) or \
			(cell_type == CELL_TYPE_CREATED) or \
			(cell_type == CELL_TYPE_DESTROY) or \
			(cell_type == CELL_TYPE_CREATE_FAILED): 
			padding = char[PADDING_CREATE]
			cell = struct.pack('>HBs', c_id, cell_type, padding)
		elif cell_type == CELL_TYPE_RELAY: 
			padding = char[PADDING_RELAY - kwargs['body_length']]
			cell = struct.pack('>HBHHIHBss', c_id, cell_type, kwargs['stream_id'],
				0x0000, kwargs['digest'], kwargs['body_length'], kwargs['relay_cmd'], kwargs['body'], padding)
		else:
			print "UNKNOWN CELL TYPE " , cell_type 
			return -1
		self.socket_buffer.put(cell)

	def getCircuit(c_id):
		return circuit_id_to_circuit_objs.get(c_id)

	# for router
	def sendRelay(self, c_id, stream_id, digest, body_length, relay_cmd, body):
		send(c_id, CELL_TYPE_RELAY, stream_id=stream_id, digest=digest, body_length=body_length, relay_cmd=relay_cmd, body=body)

	def sendRelayCell(self, cell):
		self.socket_buffer.put(cell)

	def getSourceOutgoingCircuitId(self):
		return self.source_outgoing_c_id

