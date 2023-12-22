import time
import pyaudio
import socket
import random
from RtpPacket import RtpPacket
import threading


PORT = "5004"
LIST_OF_HOSTS = ["192.168.178.83"]#["192.168.178.20", "192.168.178.102"]

data = bytes() # Stream of audio bytes 
CHUNK_SIZE = 1024
CHANNELS = 2
BROADCAST_SIZE = CHUNK_SIZE*CHANNELS*2
FORMAT = pyaudio.paInt16 # 2 bytes size
RATE = 44100

# instantiate PyAudio (1)
p = pyaudio.PyAudio()

# define callback (2)
def pyaudio_callback(in_data, frame_count, time_info, status):
    global data
    data += in_data
    return (None, pyaudio.paContinue)

def session_start():
    #data_start = bytearray(224)
    testTxt = "\x20\x00\xc4\x18\xc0\xa8\xb2\x3e\x61\x70\x70\x6c\x69\x63\x61\x74" \
            "\x69\x6f\x6e\x2f\x73\x64\x70\x00\x76\x3d\x30\x0a\x6f\x3d\x6d\x72" \
            "\x70\x69\x6e\x6b\x20\x33\x39\x31\x31\x34\x38\x35\x31\x32\x37\x20" \
            "\x30\x20\x49\x4e\x20\x49\x50\x34\x20\x31\x39\x32\x2e\x31\x36\x38" \
            "\x2e\x31\x37\x38\x2e\x36\x32\x0a\x73\x3d\x50\x75\x6c\x73\x65\x41" \
            "\x75\x64\x69\x6f\x20\x52\x54\x50\x20\x53\x74\x72\x65\x61\x6d\x20" \
            "\x6f\x6e\x20\x6d\x72\x70\x69\x6e\x6b\x2d\x75\x62\x75\x6e\x74\x75" \
            "\x0a\x63\x3d\x49\x4e\x20\x49\x50\x34\x20\x32\x32\x34\x2e\x30\x2e" \
            "\x30\x2e\x35\x36\x0a\x74\x3d\x33\x39\x31\x31\x34\x38\x35\x31\x32" \
            "\x37\x20\x30\x0a\x61\x3d\x72\x65\x63\x76\x6f\x6e\x6c\x79\x0a\x6d" \
            "\x3d\x61\x75\x64\x69\x6f\x20\x35\x30\x30\x34\x20\x52\x54\x50\x2f" \
            "\x41\x56\x50\x20\x31\x30\x0a\x61\x3d\x72\x74\x70\x6d\x61\x70\x3a" \
            "\x31\x30\x20\x4c\x31\x36\x2f\x34\x34\x31\x30\x30\x2f\x32\x0a\x61" \
            "\x3d\x74\x79\x70\x65\x3a\x62\x72\x6f\x61\x64\x63\x61\x73\x74\x0a"
    data_start = bytearray(testTxt, encoding='utf-8')
    #print(testTxt, data_start)    
    #sock.sendto(data_start, (HOST, int(9875)))

# open stream (3)
stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK_SIZE, stream_callback=pyaudio_callback)

# start the stream (4)
stream.start_stream()

seqnum = random.randint(1, 9999)
ssrc = int(time.time() * 1000.0) - 1702500000000

#1702500000000
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
try:
    #session_start()
    while True:
        if (len(data) > BROADCAST_SIZE):
            version = 2
            padding = 0
            extension = 0
            cc = 0
            marker = 0
            pt = 10 # 16bint
            seqnum = seqnum + 1
            
            rtpPacket = RtpPacket()
            rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, data[:BROADCAST_SIZE])
            data = data[BROADCAST_SIZE:]
            for host in LIST_OF_HOSTS:
                sock.sendto(rtpPacket.getPacket(), (host, int(PORT)))
            #sock.sendto(rtpPacket.getPacket(), ("192.168.178.20", int(PORT)))

except KeyboardInterrupt:
    print('\nClosing stream...')
    stream.stop_stream()
    stream.close()
    p.terminate()
    #sock.close()
