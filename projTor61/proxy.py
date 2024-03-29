# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015

import threading
import socket
import sys
import time
import string
import re
from pprint import pprint
from Queue import Queue 

def message_log(message):
	print time.strftime("%d %b %H:%M:%S").title() + " - >>> " + message 

# Exits the program
def terminate():
	print 'terminate'
	sys.exit()

class TorProxy(object):
	SLEEP_TIME_BETWEEN_RECEIVING_DATA = 0.1
	TIMEOUT = 60*10 # seconds
	SERVER_TIMEOUT = 60*10 # seconds
	SOCKET_RECV_SIZE = 1024
	TIME_THRESHOLD = 10 * 60

	class State(object):
		init = 0
		running = 1
		stopped = 2
		failed = 3

	def __init__(self):
		self.port_listening = sys.argv[3]
		self.server_is_running = True
		self.state = TorProxy.State.init

	def addRouter(self, router):
		self.router = router

	def start(self):
		print 'start'
		# ***** Create the listening thread, which dispatches child threads for each new connection ***** #
		self.state = TorProxy.State.running
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		host = socket.gethostname()
		self.server.bind((host, int(self.port_listening)))
		self.server.listen(5)
		message_log("Proxy listening on " + socket.gethostbyname(socket.gethostname()) + ":" + str(self.port_listening))

		# create thread which is accepting packets from clients
		server_connection_thread = threading.Thread(target=self.acceptConnections)
		server_connection_thread.setDaemon(True)
		server_connection_thread.start()
		return 1
	
	# Loops while server_is_running is true, accepting packets from clients 
	def acceptConnections(self):
		print 'acceptConnections'
		while self.state == TorProxy.State.running:
			(clientsocket, address) = self.server.accept()
			connection_handle_thread = threading.Thread(target=self.handle_connection, args=(clientsocket, address))
			connection_handle_thread.setDaemon(True)
			connection_handle_thread.start()

	# Does everything needed to deal with a new request from
	# a client.
	# Parses initial header from client, then contacts 
	# router-side to convey the request. This will direct
	# the router to create a stream through the Tor network 
	# and connect to the requested destination at the other end
	# of the circuit. Sends any response from other end back to client.
	# Keeps connection open if client requested a 
	# CONNECT, otherwise, simpy forwards the request.
	def handle_connection(self, clientsocket, address):
		print 'handle_connection'
		connection_closed = False
		connect_tunneling = False
		host = ""
		hostport = 80	# default

		header_buffer = ""	# to be forwarded to server for non-CONNECT requests
		header_array = []
		previous_header_line = "temp"
		current_header_line = ""

		# Buffers up the header
		while len(previous_header_line) != 0:
			curr_byte = clientsocket.recv(1) # Read the next byte
			if (curr_byte == '\n'):
				# tokenize the header lines
				line_arr = re.split(' |\t', current_header_line)
				line_buf = line_arr[0]
				for i in range(1, len(line_arr)):
					line_buf += " " + line_arr[i]
				print "tokenized current header line: " + line_buf
				header_array.append(line_buf)
				previous_header_line = current_header_line;
				current_header_line = ""
				continue
			if (curr_byte == '\r'):
				continue
			current_header_line += curr_byte

		# Reads over the headers and make modifications to the headers
		for i in range(0, len(header_array)):
			line = header_array[i]
			if i == 0:	
				line_arr = re.split(' |\t',line)
				# print line_arr
				line_arr[2] = "HTTP/1.0"
				if line_arr[0].upper() == "CONNECT":
					# print "CONNECT = TRUE"
					connect_tunneling = True
				if "https://" in line_arr[1].lower():				
					hostport = 443	
				
				header_array[0] = line_arr[0] + " " + line_arr[1] + " " + line_arr[2]
				message_log(line_arr[0] + " " + line_arr[1])	# not log the HTTP/1.0

			elif line[0:5].lower() == "host:":
				host = line[6:].lower()
				# print "host: " + host
				host_arr = host.rsplit(':', 1)		# split from the right, only split 1
				# print host_arr
				if len(host_arr) > 1:
					try:
					    port_num = int(host_arr[1])
					    host = host_arr[0]
					    hostport = port_num
					except ValueError:		# no port specified -> use default: 80 or 443
					    pass 	

			elif line.lower() == "connection: keep-alive":
				connection_closed = True
				header_array[i] = "connection: close"

			elif line.lower() == "proxy-connection: keep-alive":
				header_array[i]  = "proxy-connection: close"
			header_buffer += header_array[i] + '\n'

		# Creates a stream for this new connection on the router side
		host_address = (host, hostport)
		# startStream will send a Relay Begin cell down the circuit, then wait for Connected if success
		(connect_ret, stream_obj) = self.router.startStream(host_address)	

		if (connect_ret != 1):	
			# connect_ret = 0 -> error: Begin Failed or timeout
			print "Start stream error: " + str(connect_ret)
			return

		thisConnection = {
			"clientsocket" : clientsocket,
			"isClosed": False,
			"stream_obj" 	: stream_obj
		}
		thisConnection['prev_time'] = time.time()
		# send a 200 OK reponse 
		if connect_tunneling:	# HTTP CONNECT
			print "connect tunneling"
			clientsocket.send('HTTP/1.0 200 OK\r\n\r\n')

			connect_handle_thread = threading.Thread(target=self.handle_forwarding_to_router, args=(thisConnection,))
			connect_handle_thread.setDaemon(True)
			connect_handle_thread.start()
		else:	# not HTTP CONNECT
			# print "header: " + header_buffer
			print "NOT connect tunneling"
			retval = stream_obj.sendAllToRouter(header_buffer + "\r\n")
			if (retval < 0):
				print " when sendAllToRouter, stream_obj is close. Proxy line: 172"
				thisConnection['isClosed']
			# stream_obj.closeStream()
			# return

		# Here, we become the Proxy-side buffer-to-client writing thread
		# try:

		while time.time() - thisConnection['prev_time'] < TorProxy.TIME_THRESHOLD :
			time.sleep(TorProxy.SLEEP_TIME_BETWEEN_RECEIVING_DATA)
			# data = hostsocket.recv(SOCKET_RECV_SIZE)
			data = stream_obj.getNextFromRouter()
			if data: 
				clientsocket.sendall(data)
				# data = stream_obj.getNextFromRouter()
				thisConnection['prev_time'] = time.time()
			elif connect_tunneling:
				if thisConnection['isClosed']:
					break
			else:
				break
		# except Exception as e:
		# 	pprint(e)
		# finally:
			# print "FINALLY end thread handle_client host: " + host + ": " + str(hostport)
		clientsocket.close()
		stream_obj.closeStream()
		terminate()

	# sets the isClosed condition to True
	@staticmethod
	def timeout_function(connection):
		connection['isClosed'] = True

	def exit(self):
		pass

	# a thread for tunnel from client -> proxy -> server
	def handle_forwarding_to_router(self, thisConnection):
		print 'handle_forwarding_to_router'
		# try:
		stream_obj = thisConnection['stream_obj']
		thisConnection['prev_time'] = time.time()
		while time.time() - thisConnection['prev_time'] < TorProxy.TIME_THRESHOLD:
			time.sleep(TorProxy.SLEEP_TIME_BETWEEN_RECEIVING_DATA)

			data = thisConnection['clientsocket'].recv(TorProxy.SOCKET_RECV_SIZE)
			print data 
			if data:
				# thisConnection['hostsocket'].sendall(data)
				# TODO: Write to buffer to router side
				retval = stream_obj.sendAllToRouter(data)
				if (retval < 0):
					print " when sendAllToRouter, stream_obj is close. Proxy line: 223"
					thisConnection['isClosed']
				thisConnection['prev_time'] = time.time()
			elif thisConnection['isClosed']:
				break
		# except Exception as e:
			# pprint(e)
		# finally:
		# TODO is this right?
		stream_obj.closeStream()
		# closeSocket(thisConnection['clientsocket'])
		terminate()


	# ****** PROXY-TO-WEBSERVER communications ******
	def connect_to_server(self, host_address, stream_obj):
		print 'connect_to_server'
		# Opens a socket and connect to the server host
		hostsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		(host, hostport) = host_address 
		# print "Attempting connections to " + host + ":" + str(hostport)
		connect_ret = hostsocket.connect_ex(host_address) 

		if (connect_ret != 0):
			print "host server connection error: " + str(connect_ret)
			# router.send Relay Begin Failed down the circuit

			return -1

		thisConnection = {
				"hostsocket" : hostsocket,
				"isClosed": False,
				"stream_obj" 	: stream_obj,
				"prev_time"	:	time.time()
		}
	
		# Spawn a thread to listen to buffer and write to hostsocket

		connect_handle_thread = threading.Thread(target=self.handle_writing_to_server, args=(thisConnection,))
		connect_handle_thread.setDaemon(True)
		connect_handle_thread.start()

		connect_handle_thread = threading.Thread(target=self.handle_reading_from_server, args=(thisConnection,))
		connect_handle_thread.setDaemon(True)
		connect_handle_thread.start()

		return 1

	def handle_reading_from_server(self, thisConnection):
		print "Begin reading from server. Write to buffer."
	# try:
		while time.time() - thisConnection['prev_time'] < TorProxy.TIME_THRESHOLD:
			time.sleep(TorProxy.SLEEP_TIME_BETWEEN_RECEIVING_DATA)
			data = thisConnection['hostsocket'].recv(TorProxy.SOCKET_RECV_SIZE)
			# print "$$$$$$$$$$$$$$$$$ READ FROM SERVER: ", data
			if data: 
				retval = thisConnection['stream_obj'].sendAllToRouter(data)
				if (retval < 0):
					print " when sendAllToRouter, stream_obj is close. Proxy line: 281"
					thisConnection['isClosed']
				thisConnection['prev_time'] = time.time()
			else:
				thisConnection['isClosed'] = True
				break
		print "TIMEOUT_T reading from server."

		# except Exception as e:
		# 	pprint(e)
		# finally:
		# print "FINALLY end thread handle_client host: " + host + ": " + str(hostport)
		thisConnection['hostsocket'].close()
		thisConnection['stream_obj'].closeStream()
		terminate()

	# Read from router, send to server
	def handle_writing_to_server(self, thisConnection):
		print "begin writing to server"
		# try:
		while time.time() - thisConnection['prev_time'] < TorProxy.TIME_THRESHOLD:
			time.sleep(TorProxy.SLEEP_TIME_BETWEEN_RECEIVING_DATA)
			data = thisConnection['stream_obj'].getNextFromRouter()
			#print "WRITE TO SERVER ", data
			if data: 
				thisConnection['hostsocket'].sendall(data)
				thisConnection['prev_time'] = time.time()
			else:
				thisConnection['isClosed'] = True
				break
		print "TIMEOUT_T writing to server."
		# except Exception as e:
			# pprint(e)
		# finally:
			# print "FINALLY end thread handle_client host: " + host + ": " + str(hostport)
		thisConnection['hostsocket'].close()
		thisConnection['stream_obj'].closeStream()
		terminate()

