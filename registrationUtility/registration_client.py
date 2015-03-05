import socket
import struct
import select
import signal
import pyuv
import subprocess
import sys
import os

#-----------------------------------------------
# Usage: python registration_client.py servicePort serviceName serviceData
#   Registers a service whose IP is that the host it's running
#   on and whose port, name, and data are given on the command line.
#   Renews the registration as necessary.  Tries to unregister before
#   terminating.
# It's intended that this app be launched by
# the process that wants to be registered.
#-----------------------------------------------

#print "parent pid = ", os.getppid()
#print "my pid = ", os.getpid()

REGISTRATION_SERVER_HOST = "cse461.cs.washington.edu"
REGISTRATION_SERVER_IP = socket.gethostbyname(REGISTRATION_SERVER_HOST);
REGISTRATION_SERVER_PORT = 46101

if ( len(sys.argv) != 4 ):
    print "Usage: python ", sys.argv[0], " port name data"
    sys.exit(1)

SERVICE_PORT = int(sys.argv[1])
SERVICE_NAME = sys.argv[2]
SERVICE_DATA = int(sys.argv[3])

SERVER_RESPONSE_TIMEOUT = 4

# DO NOT CHANGE THIS. The registration service
# will send us packets on SENDING_PORT + 1
LOCAL_IP = struct.unpack('!I', socket.inet_aton(socket.gethostbyname(socket.getfqdn())))[0]
#print "[registration client] Local IP:", socket.gethostbyname(socket.getfqdn())

# Do not change anything else below here unless
# you know what you're doing
ACTION_REGISTER = int(0x01)
ACTION_REGISTERED = int(0x02)
ACTION_UNREGISTER = int(0x05)
ACTION_PROBE = int(0x06)
ACTION_ACK = int(0x07)

seq_num = 0
outstanding_packets = {}

reregistration_timer = None

# An abstraction around turning packets into bytes and back
class Packet461:
    PACKET_HEADER_FORMAT = '!HBB'  # magic word, sequence number, action
    HEADER_LENGTH = 4
    MAGIC_WORD = int(0xC461)

    def __init__(self, seq_num, action, payload):
        self.magic = Packet461.MAGIC_WORD
        self.seq_num = seq_num
        self.action = action
        self.payload = payload
        

    @classmethod
    def fromdata(cls, data):
        (magic_word, seq_num, action) = struct.unpack(Packet461.PACKET_HEADER_FORMAT, data[:Packet461.HEADER_LENGTH])
        if magic_word != Packet461.MAGIC_WORD:
            # silently drop packet
            return None
        return cls(seq_num, action, data[Packet461.HEADER_LENGTH:])

    def __str__(self):
        return "Magic: " + str(self.magic) + "\nSeqno: " + str(self.seq_num) + "\nType: " + str(self.action)

    def pack(self):
        return struct.pack( Packet461.PACKET_HEADER_FORMAT + str(len(self.payload)) + 's',
                            self.magic,
                            self.seq_num,
                            self.action,
                            self.payload)

def next_seq_num():
    global seq_num
    result = seq_num
    seq_num += 1
    return result

def bytes_to_string(string):
    return str(':'.join('{:02x}'.format(ord(c)) for c in string))
    
def shutdown(handle, signum):
    #print "[registration cient] Shutting down"
    signal_h.close()
    payload = struct.pack('!IH', LOCAL_IP, SERVICE_PORT)
    send(Packet461(next_seq_num(), ACTION_UNREGISTER, payload))
    global sending_socket
    sending_socket.close()
    global loop
    loop.stop()

def remove_packet(seq_num):
    global outstanding_packets
    if outstanding_packets[seq_num] == None:
        sys.stderr.write( "[registration client] Unexpected packet seq_num: " +  str(seq_num) + "\n")
    else:
        del outstanding_packets[seq_num]

# retransmits everything for which we haven't received a response
def rexmit(timer):
    for k,v in outstanding_packets.iteritems():
        send(v);

# convenient way of updating outstanding_packets, seq_num, and actually sending
def send(packet):
    global outstanding_packets
    outstanding_packets[packet.seq_num] = packet
    #print "[registration client] sending", bytes_to_string(packet.pack()), (REGISTRATION_SERVER_HOST, REGISTRATION_SERVER_PORT)

    global sending_socket
    return sending_socket.send((REGISTRATION_SERVER_IP, REGISTRATION_SERVER_PORT), packet.pack())

def on_read(handle, ip_port, flags, data, error):
    if data is None:
        return

    # Check that this is from the server
    if ip_port != (REGISTRATION_SERVER_IP, REGISTRATION_SERVER_PORT):
        return

    packet = Packet461.fromdata(data)
    remove_packet(packet.seq_num)
    if packet != None and packet.action == ACTION_REGISTERED:
        reregistration_timer.stop()
        (interval,) = struct.unpack("!H", packet.payload)
        reregistration_timer.start(lambda x: send_registration(), 0.8*interval, 0.8*interval)
        # isolate lease time
        # set timer for registration

def send_registration():
    register_payload = struct.pack('!IHIB' + str(len(SERVICE_NAME)) + 's',
                                   LOCAL_IP,
                                   SERVICE_PORT,
                                   SERVICE_DATA,
                                   len(SERVICE_NAME),
                                   SERVICE_NAME)
    send(Packet461(next_seq_num(),ACTION_REGISTER, register_payload))


#---------------------------------------------------------------------
# mainline
#---------------------------------------------------------------------

loop = pyuv.Loop.default_loop()

reregistration_timer = pyuv.Timer(loop)
rexmit_timer = pyuv.Timer(loop)
rexmit_timer.start(rexmit, SERVER_RESPONSE_TIMEOUT, SERVER_RESPONSE_TIMEOUT)

# Make sure we clean up and exit on Ctrl-C
signal_h = pyuv.Signal(loop)
signal_h.start(shutdown, signal.SIGINT)

#sending_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sending_socket = pyuv.UDP(loop)
sending_socket.start_recv(on_read)

# Kick things off by registering with the server
send_registration()

#print "[registration client] Sent registration!"

loop.run();

