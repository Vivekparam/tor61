from subprocess import Popen, PIPE


p = Popen(['python', 'registrationUtility/fetch.py', 'Tor61Router-0001-0001'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
output, err = p.communicate() # lol error
print err
# output = "128.208.1.179	3333	474612712\n"
print output
lines = output.split('\n')