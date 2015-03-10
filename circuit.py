# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015

import threading
from stream import TorStream

class Circuit(object):
	# this only used on the source router
	# keeps track of the state of the circuit
	# State = enum(init = 0, one_hop=1, two_hop=2, three_hop=3)
	class State(object):
		init = 0
		one_hop = 1
		two_hop = 2
		three_hop = 3

	def __init__(self, c_id):
		self.id = c_id
		self.stream_id_to_stream_objs = {}
		self.next_stream_id_num = 1
		self.next_stream_id_num_lock = threading.Lock()
		self.receive_created_condition = threading.Condition()
		self.receive_relayextend_condition = threading.Condition()
		if (self.id == 1):
			self.state = Circuit.State.init

	def getStream(self, stream_id):
		return self.stream_id_to_stream_objs[stream_id]

	def createStream(self, c_id,  stream_id=None): 
		if(stream_id == None):
			# case in which we are source router on this straem
			self.next_stream_id_num_lock.acquire()
			stream = TorStream(self.next_stream_id_num, c_id)
			self.stream_id_to_stream_objs[self.next_stream_id_num] = stream
			self.next_stream_id_num += 1
			self.next_stream_id_num_lock.release()
		else:
			stream = TorStream(stream_id, c_id)
			self.stream_id_to_stream_objs[stream_id] = stream
		return stream

	# only for the self.id == 1 circuit
	def onRelayExtended(self):
		if (self.id == 1):
			if (self.state == Circuit.State.one_hop):
				self.state = Circuit.State.two_hop
			elif (self.state == Circuit.State.two_hop):
				self.state = Circuit.State.three_hop
			print "CIRCUIT ", self.id, " STATE CHANGE TO ",  self.state

	def onCreated(self):
		if (self.id == 1):
			if (self.state == Circuit.State.init):
				self.state = Circuit.State.one_hop

	def getCid(self):
		return self.id

