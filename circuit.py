# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015

class Circuit(object):
	# this only used on the source router... 
	State = enum(init = 0, one_hop=1, two_hop=2, three_hop=3)

	def __init__(self, c_id):
		self.id = c_id
		self.stream_id_to_stream_objs = {}
		self.next_stream_id_num = 0
		if (self.id == 1):
			self.state = State.init

	def getStream(stream_id):
		return self.stream_id_to_stream_objs[stream_id]

	def createStream(): 
		# TODO: fix bad interleavings here
		stream = Stream(self.next_stream_id_num)
		self.stream_id_to_stream_objs[stream_id] = stream
		self.next_stream_id_num += 1
		return stream

	# for building circuit from this source router
	def onRelayExtend():
		if (self.state == State.one_hop):
			self.state = State.two_hop
		elif (self.state == State.two_hop):
			self.state = State.three_hop

	def onCreate():
		if (self.state == State.init):
			self.state = State.one_hop


