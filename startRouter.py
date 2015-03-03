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

	proxy.start()
	router.start()

	# Todo: health check on each other?

main()