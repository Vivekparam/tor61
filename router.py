# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015

class TorRouter(object):
	# router impl here

	def __init__(self):
		self.router_ip_to_tor_objs = {}


		x = Tor61Connection()
		def relayExtendListener(ip, port):
			#perform relay extend

		x.addRelayExtendListener(relayExtendListener)

	# This brings up the router.
	# We contact the registration service,
	# establish ourselves, then build a circuit. 
	# Returns 1 on success, 0 on failure.
	def start():
		# After constructing circuit,
		# Spawn a thread which listens for new
		# Tor61 connection attempts from others,
		# by calling startTorConnectionListener

	# Constructs a stream to given host ip:port.
	# Takes as a parameter a tuple (host, hostport)
	# Returns tuple (1, stream_obj) if stream construction 
	# was successful.
	# Returns (0, None) otherwise
	def startStream(host_address):
		# TODO
		# startStream will send a Relay Begin cell down the circuit, then start
		# a timer. If it does not recieve a response withing (10?) seconds, 
		# it will return 0, and proxy should treat this as an error.
		# If router gets back a Begin Failed, it also returns 0 and proxy treats this as an error.
		# If router gets back a Relay Connected, it sends back a 1, and proxy
		# sends back a 200 OK response. 

	# Listens on a port for incoming Tor61 connections
	# When one is built, constructs a Tor61Connection object
	# and puts it into the map router_ip_to_tor_objs
	def startTorConnectionListener(socket or something):



