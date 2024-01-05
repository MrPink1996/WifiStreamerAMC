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
AUDIO_DELAY = 4

# RTP VARIABLES
RTP_HEADER_SIZE = 12

# SOCKET VARIABLES
PORT_CTRL = 5004
PORT_TRANSMIT = 5005
PORT_SDP = 5006
SOCKET_CHUNK_SIZE = 4096 # SAMPLES
SOCKET_BROADCAST_SIZE = SOCKET_CHUNK_SIZE*AUDIO_CHANNELS*AUDIO_BYTE_SIZE + RTP_HEADER_SIZE# BYTES

class loginHandler(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.stop_thread = False
        self.hostIP = ""
        self.sockUDP = None
        self.login = False

    def run(self):
        try:
            self.sockUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sockUDP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sockUDP.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sockUDP.bind(("0.0.0.0", int(PORT_SDP)))
            self.sockUDP.settimeout(1)
            
            while True: 
                if self.stop_thread is True:
                    break

                self.sockUDP.sendto(bytes("LOGIN", "utf-8"), ("255.255.255.255", PORT_SDP))
                try:
                    # Buffer incoming broadcast message
                    data, addr = self.sockUDP.recvfrom(1024)
                    # Save Server response
                    data, addr = self.sockUDP.recvfrom(1024)
                except socket.timeout:
                    pass
                
                if data == b'OK':
                    self.hostIP = addr[0]
                    self.login = True
                    break
               
                time.sleep(2)
            self.sockUDP.close()
        except Exception as e:
            self.sockUDP.close()
   
class playAudio(threading.Thread):
    global data
    def __init__(self):
        threading.Thread.__init__(self)
        self.stop_thread = False
        self.stream = None
        self.pa = None
        self.delay = 0
        self.init = False

    def run(self):
        try:
            self.pa = pyaudio.PyAudio()
            self.stream = self.pa.open(format=AUDIO_FORMAT, channels=AUDIO_CHANNELS, rate=AUDIO_RATE, output=True, frames_per_buffer=AUDIO_CHUNK_SIZE)

            while True:
                if self.stop_thread is True:
                    break

                if len(data) == 0:
                    continue

                time_playout = float(data[0].ssrc()) + (float(data[0].timestamp())/1000000.0) + AUDIO_DELAY
                delay = time.time() - time_playout
                while(delay < 0):
                    delay = time.time() - time_playout
                self.delay = time.time() - time_playout
                self.stream.write(data[0].getPayload(), exception_on_underflow=False)
                self.init = True
                del data[0]

            self.stream.close()
            self.pa.terminate()
        except Exception as e:
            self.stream.close()
            self.pa.terminate()

class receiveAudio(threading.Thread):
    global data
    def __init__(self):
        threading.Thread.__init__(self)
        self.stop_thread = False
        self.sockUDP = None
        self.incomingData = True
        self.timeouts = 0

    def run(self):
        try:
            self.sockUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sockUDP.bind(("0.0.0.0", int(PORT_TRANSMIT)))
            self.sockUDP.settimeout(1)
            while True:
                if self.stop_thread is True:
                    break
                
                if self.incomingData is False:
                    break

                try:
                    new_data = self.sockUDP.recv(SOCKET_BROADCAST_SIZE)
                    incomingData = True
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(new_data)
                    data.append(rtpPacket)
                except socket.timeout:
                    self.timeouts = self.timeouts + 1
                    
                    if self.timeouts > 5:
                        self.incomingData = False

                time.sleep(0.01)

            # Stopping the thread
            self.sockUDP.close()
        except Exception as e:
            self.sockUDP.close()

if __name__ == "__main__":

    thread_play = playAudio()
    thread_play.start()
    LOGIN_STATE = False
    try:
        while True:
            if LOGIN_STATE is False:
                thread_login = loginHandler()
                thread_login.start()
                thread_login.join()
                LOGIN_STATE = thread_login.login
                if LOGIN_STATE is True:

                    thread_receive = receiveAudio()
                    thread_receive.start()
                continue

            LOGIN_STATE = thread_receive.incomingData
            time.sleep(2)
        
    except KeyboardInterrupt:
        thread_login.stop_thread = True
        thread_play.stop_thread = True
        thread_receive.stop_thread = True