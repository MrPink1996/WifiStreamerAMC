import pyaudio
import socket
from RtpPacket import RtpPacket
import time
import threading

## RTCP even port
data = []
RTP_HEADER_SIZE = 12
CHUNK_SIZE_SERVER = 2048
CHUNK_SIZE = 4096     # Size of frame window to write audio (frames_per_buffer)
CHANNELS = 2

## ToDo transmit neccessary variables and configurations
# CHUNKSIZE_SERVER
# IP ADDRESS CLients
# Buffer Sizes
# Broadcast size
# RATE 
# Bit Sizes
# Ports 

BROADCAST_SIZE = (CHANNELS * CHUNK_SIZE_SERVER * 2 ) + RTP_HEADER_SIZE # Socket receives audio with this size
BUFFER_SIZE = BROADCAST_SIZE * 4      # Receive this amount of data before playback
FORMAT = pyaudio.paInt16 # 2 bytes size
RATE = 44100
PORT = 5004

def getData():
    global data
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.bind(("0.0.0.0", int(PORT)))
    print(f'Socket bind succeed "0.0.0.0"')
    rtpPacket = RtpPacket()
    try:
        while True:
            new_data = sock.recv(BROADCAST_SIZE)
            rtpPacket = RtpPacket()
            rtpPacket.decode(new_data)
            data.append(rtpPacket)
    except Exception as e:
        print(e)
        print('\nClosing socket and stream...')
        sock.close()

def playData():
    global data
    smoother = 0
    try:
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK_SIZE)
        now = time.time()
        while(True):
            if(data[0].ssrc() + data[0].timestamp() <= int(time.time()*1000.0) + smoother):
                if(data[0].ssrc() + data[0].timestamp() - int(time.time() * 1000.0) > 0):
                    smoother = smoother - 1
                else:
                    smoother = smoother + 1

                if(time.time() - now > 10):
                    now = time.time()
                    print(smoother, data[0].ssrc() + data[0].timestamp() - int(time.time() * 1000.0), len(data))
                stream.write(data[0].getPayload())
                data = data[1:]
            
    except Exception as e:
        print(e)
        print('\nClosing socket and stream...')
        stream.stop_stream()
        stream.close()
        p.terminate()

def controllStream():
    global data
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.bind(("0.0.0.0", int(PORT)))
    
thread1 = threading.Thread(target=getData, args=())
thread2 = threading.Thread(target=playData, args=())
thread3 = threading.Thread(target=controllStream, args=())

thread1.start()
thread2.start()
thread1.join()