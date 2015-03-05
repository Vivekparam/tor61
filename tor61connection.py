# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015
import struct
import threading

class Tor61Connection(object):
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


	def __init__(self, partner_ip_port, socket, we_are_initiator, opener_agent_id, opened_agent_id, router):
		self.circuit_id_to_circuit_objs = {}
		self.we_are_initiator = we_are_initiator
		self.opener_agent_id = opener_agent_id
		self.opened_agent_id = opened_agent_id
		self.partner_ip_port = partner_ip_port
		self.source_outgoing_c_id = 1

		# This is the socket through which
		# the two routers will communicate
		self.socket = socket

		# We only put packaged cells into this queue
		self.socket_buffer = Queue()
		self.opened_condition = threading.Condition()

		startReaderWriter()

	# Open starts this tor61 connection.
	# In other words, it either sends back a OPENED
	# cell, or sends an OPEN cell to the other end
	# of the associated socket.
	# Returns 1 if open operation was successful
	# Returns -1 if got OPEN_FAILED
	# returns -2 if no response
	def open(self):
		if(!we_are_initiator):
			print "Open should only be called if we initiated the connection."
			return -1

		retval = -1;
		cell = None
		self.next_circuit_num = 3
		# we need to send an open, then wait for resp
		self.opened_condition.acquire()
		send(ZERO_CIRCUIT, CELL_TYPE_OPEN, opener_agent_id=self.opener_agent_id, opened_agent_id=self.opened_agent_id)
		
		# Wait for either OPENED or OPEN_FAILED response
		self.opened_condition.wait(10) # secs
		self.opened_condition.release()
		
		cell_type = self.opened_condition.cell_type

		if (cell_type == CELL_TYPE_OPENED):
			retval = 1
		elif (cell_type == CELL_TYPE_OPEN_FAILED):	
			print "received CELL_TYPE_OPEN_FAILED!"
			retval = -1
		else
			print "Did not get a response for OPEN within timeout."
			return -2
		return retval

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

	def onOpen(self):
		# we are not the initiator
		self.next_circuit_num = 0
		# need to send a opened
		send(ZERO_CIRCUIT, CELL_TYPE_OPENED, opener_agent_id=self.opener_agent_id, opened_agent_id=self.opened_agent_id)
		

	def handleCell(cell):
		c_id, cell_type, other = struct.unpack('>HBs', cell)
		if(cell_type == CELL_TYPE_OPENED):
			print "This is really weird we shouldnt be here -- CELL_TYPE_OPENED"
			self.opened_condition.cell_type = CELL_TYPE_OPENED

			self.opened_condition.acquire()
			self.opened_condition.notify()
			self.opened_condition.release()

			self.onOpened()
		elif(cell_type == CELL_TYPE_OPEN):
			# assume everything worked
			self.onOpen()
		elif(cell_type == CELL_TYPE_RELAY):

			self.onRelay(cell, self.partner_ip_port)

		elif(cell_type == CELL_TYPE_DESTROY):
			self.onDestroy(cell)
		elif(cell_type == CELL_TYPE_CREATE):
			send(c_id, CELL_TYPE_CREATED)
			self.onCreate(cell)
		elif(cell_type == CELL_TYPE_CREATED):
			self.onCreated(cell)
		elif(cell_type == CELL_TYPE_OPEN_FAILED):
			self.opened_condition.cell_type = CELL_TYPE_OPEN_FAILED
			self.opened_condition.notify()
			self.onOpenFailed(cell)
		else(cell_type == CELL_TYPE_CREATE_FAILED):
			self.onCreateFailed(cell)

	def getCircuitObj(self, c_id):
		return self.circuit_id_to_circuit_objs[c_id]

	def socket_writer(self):
		data = self.socket_buffer.get(True)
		self.socket.sendAll(data);

	# Reads data from socket, and puts still-packed
	# cell into self.socket_buffer
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

	def forward(self, c_id, cell):
		 new_cell = struct.pack_into('>H', cell, 0, c_id)

	# callbacks
	# def addOpenListener(self, callback):
	# 	self.onOpen = callback

	def addOnCreateListener(callback):
		self.onCreate = callback

	def addRelay(self, callback):
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
	def sendRelay(self, c_id, stream_id, digest, relay_cmd, body):
		send(c_id, CELL_TYPE_RELAY, stream_id=stream_id, digest=digest, body_length=0, relay_cmd=relay_cmd, body=body)

	def createNewStream(host_addr):
		stream_obj = circuit_id_to_circuit_objs.get(self.source_outgoing_c_id).createStream()
		return stream_obj

	def getSourceOutgoingCircuitId(self):
		return self.source_outgoing_c_id

