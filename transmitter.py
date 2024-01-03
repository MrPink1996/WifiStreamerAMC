import time
import pyaudio
import socket
import random
from RtpPacket import RtpPacket
import threading
import sys

data = [] # Stream of audio bytes 



# AUDIO VARIABLES
AUDIO_CHUNK_SIZE = 4096 # SAMPLES
AUDIO_CHANNELS = 2
AUDIO_FORMAT = pyaudio.paInt16 # 2 bytes size
AUDIO_BYTE_SIZE = 2
AUDIO_DELAY = 5
AUDIO_RATE = 44100
AUDIO_MAX_BUFFER_SIZE = AUDIO_RATE * AUDIO_CHANNELS * AUDIO_BYTE_SIZE #BYTES

# SOCKET VARIABLES
PORT_CTRL = 5004
PORT_TRANSMIT = 5005
PORT_AUTH = 5006
LIST_OF_HOSTS = []#["192.168.178.172", "192.168.178.102"]
SOCKET_CHUNK_SIZE = 4096 # SAMPLES
SOCKET_BROADCAST_SIZE = SOCKET_CHUNK_SIZE*AUDIO_CHANNELS*AUDIO_BYTE_SIZE # BYTES

# RTP VARIABLES
RTP_VERSION = 2
RTP_PADDING = 0
RTP_EXTENSION = 0
RTP_CC = 0
RTP_MARKER = 0
RTP_PT = 10
seqnum = random.randint(1, 9999)
ssrc = int(time.time())

# SESSION MARKERS
AUDIO_SESSION = False
UDP_SESSION = False


def ctrl_session():
    global LIST_OF_HOSTS, startTime
    
    try:
        now = time.time()
        print("start controll session")
        while True:
            if(time.time() - now > 5):
                now = time.time()
                print("list of hosts:", LIST_OF_HOSTS)
                for host in LIST_OF_HOSTS:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.connect((host, PORT_CTRL))
                        sock.sendto(str(startTime).encode(), (host, PORT_CTRL))
                    finally:
                        sock.close()
    except KeyboardInterrupt:
        print("Closing socket")
        sock.close()

def auth_session():
    global LIST_OF_HOSTS
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        print("Start authentication session")
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("0.0.0.0", PORT_AUTH))
        while True:
            data, addr = sock.recvfrom(1024)
            print(data, addr)
            if(addr[0] not in LIST_OF_HOSTS):
                LIST_OF_HOSTS.append(addr[0])

    except KeyboardInterrupt:
        sock.close()

def transmit_session():
    global seqnum, data, UDP_SESSION, AUDIO_SESSION
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    #sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        print("Starting UDP socket")
        UDP_SESSION = True
        now = time.time()
        now2 = time.time()
        packets = 0
        packets2 = 0
        while True:
            if (len(data) >= 1):
                #sock.sendto(data[0].getPacket(), ("255.255.255.255", int(PORT_TRANSMIT)))
                sock.sendto(data[0].getPacket(), ("192.168.178.172", int(PORT_TRANSMIT)))
                #for host in LIST_OF_HOSTS:
                #    sock.sendto(rtpPacket.getPacket(), (host, int(PORT_TRANSMIT)))
                packets = packets + 1
                packets2 = packets2 + 1
                data = data[1:]


            if (time.time() - now) > 5.0:
                print(f"current {packets} packets | current rate: {round(packets*SOCKET_BROADCAST_SIZE*8/((time.time() - now)*1000000), 2)} Mb/s | remaining packets: {len(data)} | total packets: {packets2} | total rate: {round(packets2*SOCKET_BROADCAST_SIZE*8/((time.time() - now2)*1000000), 2)} Mb/s ")
                now = time.time()
                packets = 0

            #if( packets2 >= 3000):
            #    print(f"current {packets} packets | current rate: {round(packets*SOCKET_BROADCAST_SIZE*8/((time.time() - now)*1000000), 2)} Mb/s | remaining packets: {len(data)} | total packets: {packets2} | total rate: {round(packets2*SOCKET_BROADCAST_SIZE*8/((time.time() - now2)*1000000), 2)} Mb/s ")
            #    sock.close()
            #    break

            if(AUDIO_SESSION == False and len(data) == 0):
                print('\nClosing UDP socket...')
                sock.close()
                break
    except KeyboardInterrupt:
        print('\nClosing UDP socket...')
        sock.close()

def record_session():
    global AUDIO_SESSION
    p = pyaudio.PyAudio()
    stream = p.open(format=AUDIO_FORMAT, channels=AUDIO_CHANNELS, rate=AUDIO_RATE, input=True, frames_per_buffer=AUDIO_CHUNK_SIZE, stream_callback=pyaudio_callback)
    stream.start_stream()
    try:
        AUDIO_SESSION = True
        print("Start recording audio")
        while True:
            pass
    except KeyboardInterrupt:
        print('\nStop recording audio')
        stream.stop_stream()
        stream.close()
        p.terminate()
        AUDIO_SESSION = False

def pyaudio_callback(in_data, frame_count, time_info, status):
    global data, seqnum, ssrc
    seqnum = seqnum + 1
    rtpPacket = RtpPacket()
    rtpPacket.encode(RTP_VERSION, RTP_PADDING, RTP_EXTENSION, RTP_CC, seqnum, RTP_MARKER, RTP_PT, ssrc, time_info['input_buffer_adc_time'], in_data)
    data.append(rtpPacket)
    return (None, pyaudio.paContinue)


if __name__ == "__main__":
    thread_authenticate = threading.Thread(target=auth_session, args=())
    thread_ctrl = threading.Thread(target=ctrl_session, args=())
    thread_transmit = threading.Thread(target=transmit_session, args=())
    thread_record = threading.Thread(target=record_session, args=())

    thread_record.start()

    while(not AUDIO_SESSION):
        pass
    thread_transmit.start()
    thread_transmit.join()
