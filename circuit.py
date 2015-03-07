# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015

class Circuit(object):
	# this only used on the source router
	# keeps track of the state of the circuit
	State = enum(init = 0, one_hop=1, two_hop=2, three_hop=3)

	def __init__(self, c_id):
		self.id = c_id
		self.stream_id_to_stream_objs = {}
		self.next_stream_id_num = 0
		self.receive_created_condition = thread.Condition()
		self.receive_relayextend_condition = thread.Condition()
		if (self.id == 1):
			self.state = State.init

	def getStream(self, stream_id):
		return self.stream_id_to_stream_objs[stream_id]

	def createStream(self): 
		# TODO: fix bad interleavings here
		stream = Stream(self.next_stream_id_num)
		self.stream_id_to_stream_objs[stream_id] = stream
		self.next_stream_id_num += 1
		return stream

	# only for the self.id == 1 circuit
	def onRelayExtended(self):
		if (self.id == 1):
			if (self.state == State.one_hop):
				self.state = State.two_hop
			elif (self.state == State.two_hop):
				self.state = State.three_hop

	def onCreated(self):
		if (self.id == 1):
			if (self.state == State.init):
				self.state = State.one_hop

	def getCid(self):
		return self.id

