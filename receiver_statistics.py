import pyaudio
import socket
from RtpPacket import RtpPacket
import time
import threading
import random
import struct


## RTCP even port
data = []
timeStart = 0

# AUDIO VARIABLES
AUDIO_CHUNK_SIZE = 1024 # SAMPLES
AUDIO_CHANNELS = 2
AUDIO_FORMAT = pyaudio.paInt16 # 2 bytes size
AUDIO_BYTE_SIZE = 2
AUDIO_RATE = 44100
AUDIO_DELAY = (AUDIO_CHUNK_SIZE/AUDIO_RATE) * 128

# RTP VARIABLES
RTP_HEADER_SIZE = 12

# SOCKET VARIABLES
SERVER_IP = ""
PORT_SYNC = 5003
PORT_CTRL = 5004
PORT_TRANSMIT = 5005
PORT_SDP = 5006
SOCKET_CHUNK_SIZE = 1024 # SAMPLES
SOCKET_BROADCAST_SIZE = SOCKET_CHUNK_SIZE*AUDIO_CHANNELS*AUDIO_BYTE_SIZE + RTP_HEADER_SIZE# BYTES
        
class receiveAudio(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.stop_thread = False
        self.sockUDP = None
        self.timeouts = 0
        self.receivingTimes = []
        self.receivedSeqNum = []
        self.scriptFinished = False
        self.jitter = [0]
        self.counter = 0
        self.receivedTimestamps = [time.time()]
kaiiak
    def run(self):
        global data, SERVER_IP
        try:
            self.sockUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sockUDP.bind(('', int(PORT_TRANSMIT)))
            group = socket.inet_aton('224.3.29.71')
            mreq = struct.pack('4sL', group, socket.INADDR_ANY)
            self.sockUDP.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            self.sockUDP.settimeout(1)
            
            while True:
                # Stop the thread when variable is set through main program
                if self.stop_thread is True:
                    break
                if self.timeouts >= 20: 
                    break

                try:
                    new_data, address = self.sockUDP.recvfrom(SOCKET_BROADCAST_SIZE)
                    self.counter = self.counter + 1
                    
                    D = abs(time.time() - self.receivedTimestamps[-1])
                    self.receivedTimestamps.append(time.time())
                    self.jitter.append(self.jitter[self.counter - 1] + ((D - self.jitter[self.counter - 1] ) / 16))


                    self.receivingTimes.append(time.time())
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(new_data)
                    self.receivedSeqNum.append(rtpPacket.seqNum())
                    data.append(rtpPacket)
                except socket.timeout:
                    if len(data) > 0:
                        self.timeouts = self.timeouts + 1
                    
            f = open("receiverStatsSeqNum.txt", "w")
            for item in self.receivedSeqNum:
                f.write(str(item) + "\n")
            f = open("receiverStatsReceivingTimes.txt", "w")
            for item in self.receivingTimes:
                f.write(str(item) + "\n")
            f = open("jitterRTP.txt", "w")
            for item in self.jitter:
                f.write(str(item) + "\n")
            print("written data to file")
            # Stopping the thread
            self.sockUDP.close()
        except Exception as e:
            print(e)

        self.scriptFinished = True

if __name__ == "__main__":
    # Start Receiving Audio
    thread_receive = receiveAudio()
    thread_receive.start()
    # Main loop and display informations
    try:
        while True:
            time.sleep(2)
            if(thread_receive.scriptFinished is True):
                break
            
    except KeyboardInterrupt:
        thread_receive.stop_thread = True

        

