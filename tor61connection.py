# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015
import struct

class Tor61Connection(object):
	ZERO_CIRCUIT = 0x0000
	CELL_TYPE_OPEN = 0x05
	CELL_TYPE_OPENED = 0x06
	CELL_TYPE_OPEN_FAILED = 0x07
	CELL_TYPE_CREATE = 0x01
	CELL_TYPE_CREATED = 0x02
	CELL_TYPE_CREATE_FAILED = 0x08
	CELL_TYPE_DESTROY = 0x04
	CELL_TYPE_RELAY = 0x03


	def __init__(self, ip_port, socket, we_are_initiator, opener_agent_id, opened_agent_id, router):
		self.circuit_id_to_circuit_objs = {}
		self.we_are_initiator = we_are_initiator
		self.opener_agent_id = opener_agent_id
		self.opened_agent_id = opened_agent_id

		# This is the socket through which
		# the two routers will communicate
		self.socket = socket

		# We only put packaged cells into this queue
		self.socket_buffer = Queue()


	def open(self):
		retval = -1;
		cell = None
		if(we_are_initiator):
			self.next_circuit_num = 1
			# we need to send an open, then wait for resp
			# 2, 1, 4, 4
			cell = struct.pack('>HBII', ZERO_CIRCUIT, CELL_TYPE_OPEN, self.opener_agent_id, self.opened_agent_id)
			self.socket_buffer.put(cell)
			# Now, we expect to get an OPENED in response
			length_received = 0
			opened_cell = ""
			while (length_received < 512)
				data = self.socket.recv(512 - length_received)
				if not (data):
					print "no more received data"
					# on error
					break
				else:
					opened_cell += data

			# assume everything worked
			c_id, cell_type, opener_agent_id, opened_agent_id, padding = struct.unpack('>HBIIs', opened_cell)
			if (cell_type == CELL_TYPE_OPENED):
				retval = 1
			elif (cell_type == CELL_TYPE_OPEN_FAILED):	
				print "received CELL_TYPE_OPEN_FAILED!"
				retval = -1
		else:
			# we are not the initiator
			self.next_circuit_num = 0
			# need to send a opened
			padding = char[512 - 11]
			cell = struct.pack('>HBIIs', ZERO_CIRCUIT, CELL_TYPE_OPENED, self.opener_agent_id, self.opened_agent_id, padding)
			self.socket_buffer.put(cell)
			retval = 1
		
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
		c_id, cell_type, opener_agent_id, opened_agent_id, padding = struct.unpack('>HBIIs', cell)
		if(cell_type == CELL_TYPE_OPENED):
			print "This is really weird we shouldnt be here -- CELL_TYPE_OPENED"
		elif(cell_type == CELL_TYPE_OPEN):
			self.onOpen(cell)
		elif(cell_type == CELL_TYPE_RELAY):
			self.onRelay(cell)
		elif(cell_type == CELL_TYPE_DESTROY):
			self.onDestroy(cell)
		elif(cell_type == CELL_TYPE_CREATE):
			self.onCreate(cell)
		elif(cell_type == CELL_TYPE_CREATED):
			self.onCreated(cell)
		elif(cell_type == CELL_TYPE_OPEN_FAILED):
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

	def sendBegin(c_id (?), ip, port):

	def sendData():

	# callbacks
	def addOpenListener(self, callback):
		self.onOpen = callback

	def addRelay(self, callback):
		self.onRelayBegin = callback
