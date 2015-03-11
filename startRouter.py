# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015
from proxy import TorProxy
from router import TorRouter
import threading
import sys
# ***** We create a separate thread to read for eof from console ***** #

IS_RUNNING = True
# Loops until reading eof or 'q'
# from stdin, then sets server_is_running
# to false and terminates thread.
router = None
proxy = None
def readForEof():
	try: 
		while True:
			uin = sys.stdin.readline().strip()
			if not uin or (uin is 'q'):
				if not uin: print "eof -- exiting"
				# got eof
				IS_RUNNING = False
				sys.exit()
	except KeyboardInterrupt:
		server_is_running = False
		print "calling exit"
		exit()

def exit():
	router.exit()
	proxy.exit()
	sys.exit()

def terminate(router):
	router.killRouter()
	return

def main():
		# Create thread which reads from stdin
	# user_input_thread = threading.Thread(target=readForEof)
	# user_input_thread.setDaemon(True)
	# user_input_thread.start()
	global proxy
	global router
	proxy = TorProxy()
	router = TorRouter()
	proxy.addRouter(router)
	router.addProxy(proxy)
	# Now, both sides have the state they need

	ret = proxy.start()
	if(ret != 1) :
		print "Error starting proxy."
		terminate(router)
		exit()
	
	ret = router.start()
	if(ret < 0) :
		print "Error starting router."
		terminate(router)
		exit()

	try: 
		while True:
			uin = sys.stdin.readline().strip()
			if not uin or (uin is 'q'):
				if not uin: print "eof -- exiting"
				break
	except KeyboardInterrupt:
		print "calling exit"
	finally:
		exit()


	# Todo: health check on each other?

main()