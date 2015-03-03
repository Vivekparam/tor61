# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015

import threading
import socket
import sys
import time
import string
import re
from pprint import pprint

SLEEP_TIME_BETWEEN_RECEIVING_DATA = 0.1
TIMEOUT = 10 # seconds
SOCKET_RECV_SIZE = 1024
server_is_running = True
port_listening = sys.argv[1]

# Exits the program
def terminate():
	sys.exit()

def message_log(message):
	print time.strftime("%d %b %H:%M:%S").title() + " - >>> " + message 

# sets the isClosed condition to True
def timeout_function(connection):
	connection['isClosed'] = True

# resets the timer for both tunnels 
def reset_timer(connection):
	#print "set_timer"
	connection['timerLock'].acquire() 
	timer = connection['timer']
	if timer is not None:
		timer.cancel()
	timer = threading.Timer(TIMEOUT, timeout_function, (connection,))
	timer.start()
	connection['timerLock'].release() 

def closeSockets(clientsocket, hostsocket):
	clientsocket.close()	
	hostsocket.close()

# a thread for tunnel from client -> proxy -> server
def handle_forwarding_to_server(thisConnection):
	# print "new thread: handle_forwarding_to_server"
	# pprint(thisConnection)
	# connect_tunneling == True
	try:
		while True:
			time.sleep(SLEEP_TIME_BETWEEN_RECEIVING_DATA)
			data = thisConnection['clientsocket'].recv(SOCKET_RECV_SIZE) 
			reset_timer(thisConnection)
			if data:
				thisConnection['hostsocket'].sendall(data)
			elif thisConnection['isClosed']:			# half close? do we need an isClosed condition for each tunnel?
				break
			else:
				break
	except Exception as e:
		pprint(e)
	finally:
		# print "FINALLY end thread handle_forwarding_to_server"
		closeSockets(thisConnection['clientsocket'], thisConnection['hostsocket'])
		terminate()

# ***** RENAME THIS CHUNK LATER ***** #
def handle_client(clientsocket, address):
	# print "thread: handle_client"
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
			# print "tokenized current header line: " + line_buf
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

	# Opens a socket and connect to the server host
	hostsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	host_address = (host, hostport)
	# print "Attempting connections to " + host + ":" + str(hostport)
	connect_ret = hostsocket.connect_ex(host_address) 
	if (connect_ret != 0):
		print "host server connection error: " + str(connect_ret)

	if connect_tunneling:	# HTTP CONNECT
		clientsocket.send('HTTP/1.0 200 OK\r\n\r\n')
		thisConnection = {
			"clientsocket" : clientsocket,
			"hostsocket" : hostsocket,
			"isClosed": False,
			"timerLock" : threading.Lock()
		}
		# initialize and start timer
		timer = threading.Timer(TIMEOUT, timeout_function, (thisConnection,))
		timer.start()
		thisConnection['timer'] = timer

		connect_handle_thread = threading.Thread(target=handle_forwarding_to_server, args=(thisConnection,))
		connect_handle_thread.setDaemon(True)
		connect_handle_thread.start()
	else:	# not HTTP CONNECT
		# print "header: " + header_buffer
		hostsocket.sendall(header_buffer + "\r\n")

	try:
		while True:
			time.sleep(SLEEP_TIME_BETWEEN_RECEIVING_DATA)
			data = hostsocket.recv(SOCKET_RECV_SIZE)
			if data: 
				clientsocket.sendall(data)
			elif connect_tunneling:
				if thisConnection['isClosed']:
					break
				reset_timer(thisConnection)
			else:
				break
	except Exception as e:
		pprint(e)
	finally:
		# print "FINALLY end thread handle_client host: " + host + ": " + str(hostport)
		closeSockets(clientsocket, hostsocket)
		terminate()

# ***** We create a separate thread to read for eof from console ***** #

# Loops until reading eof or 'q'
# from stdin, then sets server_is_running
# to false and terminates thread.
def readForEof():
	global server_is_running
	try: 
		while True:
			uin = sys.stdin.readline().strip()
			if not uin or (uin is 'q'):
				if not uin: print "eof"
				# got eof
				server_is_running = False
				terminate()
	except KeyboardInterrupt:
		server_is_running = False
		terminate()

# Create thread which reads from stdin
user_input_thread = threading.Thread(target=readForEof)
user_input_thread.setDaemon(True)
user_input_thread.start()

# ***** Create the listening thread, which dispatches child threads for each new connection ***** #
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = socket.gethostname()
server.bind((host, int(port_listening)))
server.listen(5)
message_log("Proxy listening on " + socket.gethostbyname(socket.gethostname()) + ":" + port_listening)

# Loops while server_is_running is true, accepting packets from clients 
def acceptConnections():
	global server_is_running
	while server_is_running:
		(clientsocket, address) = server.accept()
		# perform basic packet handling then put it in a queue
		# create thread which deals with this cleint
		connection_handle_thread = threading.Thread(target=handle_client, args=(clientsocket, address))
		connection_handle_thread.setDaemon(True)
		connection_handle_thread.start()

# create thread which is accepting packets from clients
server_connection_thread = threading.Thread(target=acceptConnections)
server_connection_thread.setDaemon(True)
server_connection_thread.start()

# ***** Keep server alive until it is time ***** # 
# Exit when server stops running
while server_is_running:
	# loop de loop
	continue

server.close()
terminate()

