# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015
import proxy
import router

def main():
	proxy = TorProxy()
	router = TorRouter()
	proxy.addRouter(router)
	router.addProxy(proxy)
	# Now, both sides have the state they need

	ret = proxy.start()
	if(ret != 1) {
		print "Error starting proxy."
	}
	ret = router.start()
	if(ret != 1) {
		print "Error starting router."
	}
	# Todo: health check on each other?

main()