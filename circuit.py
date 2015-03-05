# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015

class Circuit(object):

	def __init__(self, c_id):
		self.id = c_id
		self.stream_id_to_stream_objs = {}
		self.next_stream_id_num = 0

	def getStream(stream_id):

	def createStream(): 
		# TODO: fix bad interleavings here
		stream = Stream(self.next_stream_id_num)
		self.stream_id_to_stream_objs[stream_id] = stream
		self.next_stream_id_num += 1
		return stream


