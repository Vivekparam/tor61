# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015

from Queue import Queue 

# A stream object represents 
# a Tor stream on a circuit
class TorStream(object):

	def __init__(self, streamNum):
		# go through the entire stream creation process as outlined
		# in the powerpoint.
		# spawn threads to listen to buffers
		self.bufferToProxy = Queue()
		self.bufferToRouter = Queue()
		self.streamNum = streamNum

	def closeStream(self):

	# Define the operations which transfer data from 
	# Buffer to Proxy and vice-versa

	def getNextFromRouter(self):
		return self.bufferToProxy.get(True) # block until something is there

	def getNextFromProxy(self):
		return self.bufferToRouter.get(True) # block until something is there

	def sendAllToRouter(self, data):
		self.bufferToRouter.put(data)

	def sendAllToProxy(self, data):
		self.bufferToProxy.put(data)