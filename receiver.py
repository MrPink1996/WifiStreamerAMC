import pyaudio
import socket
from RtpPacket import RtpPacket
import time
import threading
import random 

## RTCP even port
data = []

# AUDIO VARIABLES
AUDIO_CHUNK_SIZE = 4096 # SAMPLES
AUDIO_CHANNELS = 2
AUDIO_FORMAT = pyaudio.paInt16 # 2 bytes size
AUDIO_BYTE_SIZE = 2
AUDIO_RATE = 44100
AUDIO_DELAY = 5

# RTP VARIABLES
RTP_HEADER_SIZE = 12

# SOCKET VARIABLES
PORT_CTRL = 5004
PORT_TRANSMIT = 5005
PORT_AUTH = 5006
LIST_OF_HOSTS = []#["192.168.178.172", "192.168.178.102"]
SOCKET_CHUNK_SIZE = 4096 # SAMPLES
SOCKET_BROADCAST_SIZE = SOCKET_CHUNK_SIZE*AUDIO_CHANNELS*AUDIO_BYTE_SIZE + RTP_HEADER_SIZE# BYTES


def receive_session():
    global data
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("0.0.0.0", int(PORT_TRANSMIT)))
    print(f'Socket bind succeed "0.0.0.0"')
    rtpPacket = RtpPacket()
    try:
        packets = 0
        packets2 = 0
        now2 = time.time()
        now = time.time()
        while True:
            new_data = sock.recv(SOCKET_BROADCAST_SIZE)
            rtpPacket = RtpPacket()
            rtpPacket.decode(new_data)

            data.append(rtpPacket)
            packets = packets + 1
            packets2 = packets2 + 1
            # if(len(data) >= 64):
            #     data = data[1:]
            if( time.time() - now > 5.0):
                print(f"current {packets} packets | current rate {round(packets*SOCKET_BROADCAST_SIZE*8/((time.time() - now)*1000000), 2)} Mb/s | remaining packet: {len(data)} | total {packets2} packets | total rate {round(packets2*SOCKET_BROADCAST_SIZE*8/((time.time() - now2)*1000000), 2)} Mb/s")
                now = time.time()
                packets = 0


    except Exception as e:
        print(e)
        print('\nClosing socket and stream...')
        sock.close()

now = time.time()

def output_callback(in_data, frame_count, time_info, status):
    global data, now
    #print(time_info)
    while(len(data) == 0):
        pass
    outdata = data[0]
    
    time_playout = float(outdata.ssrc()) + (float(outdata.timestamp())/1000000.0) + AUDIO_DELAY
    delay = time_info['output_buffer_dac_time'] - time_playout

    if(time.time() - now > 5):        
        print(f"playout time: {round(time_playout, 2)} | current time: {round(time.time(), 2)} | delay: {round(delay*1000000.0, 2)} us")
        now = time.time()
    print(delay)
    if(delay < 0):
        return (outdata.getPayload(), pyaudio.paContinue)
    else:
        data = data[1:]
        return (outdata.getPayload(), pyaudio.paContinue)

def play_session_callback():
    try:
        p = pyaudio.PyAudio()
        stream = p.open(format=AUDIO_FORMAT, channels=AUDIO_CHANNELS, rate=AUDIO_RATE, output=True, frames_per_buffer=AUDIO_CHUNK_SIZE, stream_callback=output_callback)
        # Wait for stream to finish (4)
        while stream.is_active():
            time.sleep(0.1)
    finally:
        stream.close()
        p.terminate()

def play_session_blocking():
    global data
    smoother = 0
    try:
        p = pyaudio.PyAudio()
        stream = p.open(format=AUDIO_FORMAT, channels=AUDIO_CHANNELS, rate=AUDIO_RATE, output=True, frames_per_buffer=AUDIO_CHUNK_SIZE)
        now = time.time()
        while(True):
            if( len(data) < 1):
                continue

            time_playout = float(data[0].ssrc()) + (float(data[0].timestamp())/1000000.0) + AUDIO_DELAY
            delay = time.time() - time_playout
            if(delay > 0.0001):
                #print("too late")
                data = data[1:]
                continue

            if(delay < - 0.0001):
                #print("too early")
                s = random.random() * 0.0001
                #print(s)
                time.sleep(s)
                continue

            #print(delay)
            stream.write(data[0].getPayload())
            data = data[1:]
        
            if(time.time() - now > 2.0):
                now = time.time()
                print(f"playout time: {round(time_playout, 2)} | current time: {round(time.time(), 2)} | delay: {round(delay*1000000.0, 2)} us | remaining packets: {len(data)}")
                # if(delay >= 0.0001):
                #     k = (delay * AUDIO_RATE / AUDIO_CHUNK_SIZE)
                #     print("skip packets: ", k)
                #     data = data[min(len(data), int(k) + 1):]



            
    except Exception as e:
        print(e)
        print('\nClosing socket and stream...')
        stream.stop_stream()
        stream.close()
        p.terminate()

def ctrl_session():
    global startTime
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("0.0.0.0", PORT_CTRL))
        sock.listen(10)
        while True:
            print('waiting for a connection')
            connection, client_address = sock.accept()
            try:
                print('connection from', client_address)
                data = connection.recv(1024)
                startTime = int(data.decode("utf-8"))
                print(data, startTime)
            finally:
                print("closing connection")
                connection.close()
    except KeyboardInterrupt:
        print("Closing socket")
        sock.close()
    
def auth_session():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)  # UDP
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(bytes("I Want to Start, Client1", "utf-8"), ("255.255.255.255", PORT_AUTH))
    time.sleep(1)
    sock.close()


thread_auth = threading.Thread(target=auth_session, args=())
thread_receive = threading.Thread(target=receive_session, args=())
thread_play = threading.Thread(target=play_session_blocking, args=())
#thread_play = threading.Thread(target=play_session_callback, args=())
thread_ctrl = threading.Thread(target=ctrl_session, args=())


thread_play.start()
thread_receive.start()
thread_receive.join()
#thread_play.join()