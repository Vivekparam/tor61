import socket
import struct
import signal
import subprocess
import sys
import pyuv

import linecache

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    print 'EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)

# Usage: python fetch.py namePrefix
#   Prints to stdout the returned entries in format
#      nameString intVal  IP port\n
#      ...

# Change these as necessary
REGISTRATION_SERVICE_HOST = "cse461.cs.washington.edu"
REGISTRATION_SERVICE_IP = socket.gethostbyname(REGISTRATION_SERVICE_HOST);
REGISTRATION_SERVICE_PORT = 46101

SERVER_RESPONSE_TIMEOUT = 3

ACTION_FETCH = int(0x03)
ACTION_FETCH_RESPONSE = int(0x04)

seq_num = 0
outstanding_packets = {}
timeouts_without_register = 0

remaining_sends = 3

if len(sys.argv) != 2:
    print "Usage: python ./fetch.py serviceName"
    sys.exit(1)
fetchKey = sys.argv[1]

# An abstraction around turning packets into bytes and back
class Packet461:
    PACKET_HEADER_FORMAT = '!HBB'  # magic word, sequence number, action
    HEADER_LENGTH = 4
    MAGIC_WORD = int(0xC461)

    def __init__(self, action, payload):
        self.magic = Packet461.MAGIC_WORD
        global seq_num
        self.seq_num = seq_num
        seq_num += 1
        self.action = action
        self.payload = payload

    @classmethod
    def fromstring(cls, string):
        # print bytes_to_string(string)
        (magic_word, seq_num, action) = struct.unpack(Packet461.PACKET_HEADER_FORMAT, string[:Packet461.HEADER_LENGTH])
        if magic_word != Packet461.MAGIC_WORD:
            return None
        packet = cls(action, string[Packet461.HEADER_LENGTH:])
        packet.seq_num = seq_num
        return packet

    def __str__(self):
        return "Magic: " + str(self.magic) + "\nSeqno: " + str(self.seq_num) + "\nType: " + str(self.action)

    def pack(self):
        return struct.pack(Packet461.PACKET_HEADER_FORMAT + str(len(self.payload)) + 's',
                           Packet461.MAGIC_WORD,
                           self.seq_num,
                           self.action,
                           self.payload)
    @classmethod
    def parseFetchResponseEntry(cls, data):
        # print bytes_to_string(data)
        entry = { 'ip': None, 'port': None, 'data': None}
        (entry['ip'], entry['port'], entry['data']) = struct.unpack("!IHI", data)
        entry['ip'] = socket.inet_ntoa(hex(entry['ip'])[2:].zfill(8).decode('hex'))
        return entry


def bytes_to_string(string):
    return str(':'.join('{:02x}'.format(ord(c)) for c in string))

# convenient way of updating outstanding_packets, seq_num, and actually sending
def send(timer):
    global fetch_packet
    packet = fetch_packet
    global outstanding_packets
    outstanding_packets[packet.seq_num] = packet
    #print ("[registration service] sending",
    #       bytes_to_string(packet.pack()),
    #      (REGISTRATION_SERVICE, REGISTRATION_PORT))

    global sending_socket
    sending_socket.send((REGISTRATION_SERVICE_IP, REGISTRATION_SERVICE_PORT), packet.pack())
    global remaining_sends
    remaining_sends -= 1
    if ( remaining_sends <= 0 ):
        global loop
        loop.stop()

def on_read(handle, address, flags, raw, error):
    if error:
        print error
        sys.exit(0)
    # raw, address = sending_socket.recvfrom(1024)
    packet = Packet461.fromstring(raw)
    if packet and packet.action == ACTION_FETCH_RESPONSE:
        (packet.numFetchEntries,) = struct.unpack("!B", packet.payload[0])
        # print str(packet.numFetchEntries) + " entries"
        offset = 1;
        for e in xrange(packet.numFetchEntries):
            entry = Packet461.parseFetchResponseEntry(packet.payload[offset:offset+10])
            print str(entry['ip']) + "\t" + str(entry['port']) + "\t" + str(entry['data'])
            offset += 10
        global loop
        loop.stop()

loop = pyuv.Loop.default_loop()

sending_socket = pyuv.UDP(loop)
sending_socket.start_recv(on_read)

payload = struct.pack('!B' + str(len(fetchKey)) + 's', len(fetchKey), fetchKey)
fetch_packet = Packet461(ACTION_FETCH, payload)

rexmit_timer = pyuv.Timer(loop)
rexmit_timer.start(send, 0, SERVER_RESPONSE_TIMEOUT)


loop.run()
