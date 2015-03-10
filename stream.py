# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015

from Queue import Queue 
import threading
import struct
from pprint import pprint
# A stream object represents 
# a Tor stream on a circuit
class TorStream(object):
	class State(object):
		init = 0
		running = 1
		stopped = 2
		failed = 3

	STREAM_ZERO_RELAY_EXTEND = 0x0000

	CELL_TYPE_RELAY = 0x03
	RELAY_CMD_DATA = 0x02
	PADDING_RELAY = 512 - 2 -1 -2 -2 - 4 - 2 - 1
	RELAY_DIGEST_CONSTANT = 0

	# class State(Enum):
	# 	init = 0
	# 	running = 1
	# 	stopped = 2

	def __init__(self, streamNum, c_id):
		# go through the entire stream creation process as outlined
		# in the powerpoint.
		# spawn threads to listen to buffers
		self.bufferToProxy = Queue()
		self.bufferToRouter = Queue()
		self.streamNum = streamNum
		self.state = TorStream.State.init
		self.c_id = c_id
		self.connected_condition = threading.Condition()

	def lockForConnected(self):
		self.connected_condition.acquire()

	def unlockForConnected(self):
		self.connected_condition.release()

	def waitForConnected(self, timeout):
		print "Waiting for connected"
		self.connected_condition.wait(timeout)

	def notifyConnected(self):
		print "Stream connected"
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
		return False

	def closeStream(self):
		# self.state = TorStream.State.stopped
		pass

	# Define the operations which transfer data from 
	# Buffer to Proxy and vice-versa

	def getNextFromRouter(self):
		data = self.bufferToProxy.get(True) # block until something is there
		print "GOT DATA FROM ROUTER. RETURNING IT ", data
		return data

	def getNextFromProxy(self):
		data = self.bufferToRouter.get(True) # block until something is there
		print "&&&&&&&&&&&&&&&&&&&&&&&&&&&GOT DATA FROM PROXY. RETURNING IT ", data

		return data

	# Multiplexes to router side / tor61 network
	def sendAllToRouter(self, data):
		entire_data = data
		while(len(entire_data) > 0):
			data = entire_data[:400]
			print "SENDDDDDDING FROM CLIENT TO ROUTER: ", data 
			zeroes = 0x0000
			# print 'padding length of ' + str(Tor61Connection.PADDING_RELAY - kwargs['body_length'])
			# print 'body length of ' + str(len( kwargs['body']))
			
			body = data
			body_len = len(data)
			cell = struct.pack('>HBHHIHB%ds' % (body_len,) + ('x' * (TorStream.PADDING_RELAY - body_len)) , self.c_id, TorStream.CELL_TYPE_RELAY, self.streamNum, 
								zeroes, TorStream.RELAY_DIGEST_CONSTANT, body_len, TorStream.RELAY_CMD_DATA, body)
			print "--------------- mulitplexing and SENDDDDDDING to buffer:"
			print "new_c_id ", self.c_id
			print "cell_type", TorStream.CELL_TYPE_RELAY
			print "stream_id", self.streamNum
			print "Zeroes", zeroes
			print "digest", TorStream.RELAY_DIGEST_CONSTANT
			print "body_length", body_len
			print "relay_cmd", TorStream.RELAY_CMD_DATA
			print "body_padding", body
			print "----------------------------------"
			# print 'sending cell length of: ' + str(len(cell))
			self.bufferToRouter.put(cell)
			# pprint(self.bufferToRouter)
			entire_data = entire_data[400:]

	# Demultplexes to send to proxy / server network
	def sendAllToProxy(self, data):
		print "SENDDDDDDING TO PROXY: ", data 
		# demultiplexing happens in the router.handleRelay
		self.bufferToProxy.put(data)

	def sendOKOverTCP(self):
		ok_message = ('HTTP/1.0 200 OK\r\n\r\n')
		self.bufferToProxy.put(ok_message)



