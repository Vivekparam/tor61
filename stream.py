# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015

from Queue import Queue 
from threading

# A stream object represents 
# a Tor stream on a circuit
class TorStream(object):
	class State(object):
		init = 0
		running = 1
		stopped = 2
		failed = 3

	STREAM_ZERO_RELAY_EXTEND = 0x0000

	# class State(Enum):
	# 	init = 0
	# 	running = 1
	# 	stopped = 2

	def __init__(self, streamNum):
		# go through the entire stream creation process as outlined
		# in the powerpoint.
		# spawn threads to listen to buffers
		self.bufferToProxy = Queue()
		self.bufferToRouter = Queue()
		self.streamNum = streamNum
		self.state = TorStream.State.init
		self.connected_condition = threading.Condtion()

	def lockForConnected(self):
		self.connected_condition.acquire()

	def unlockForConnected(self):
		self.connected_condition.release()

	def waitForConnected(self, timeout):
		self.connected_condition.wait(timeout)

	def notifyConnected(self):
		self.connected_condition.acquire()
		self.state = TorStream.State.running
		self.connected_condition.notify()
		self.connected_condition.release()

	def notifyFailed(self):
		self.connected_condition.acquire()
		self.connected_condition.success = 0
		self.state = TorStream.State.failed
		self.connected_condition.notify()
		self.connected_condition.release()

	def checkState(self):


	def closeStream(self):
		self.state = TorStream.State.stopped

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

	def sendOKOverTCP(self):
		ok_message = ('HTTP/1.0 200 OK\r\n\r\n')
		self.bufferToProxy.put(ok_message)



