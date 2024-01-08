import pyaudio
import socket
from RtpPacket import RtpPacket
import time
import threading
import random
import logging

# Configurations for console and file logger
# Configurations for console and file logger
logger = logging.getLogger("RTP Audio Client")
logfile_handle = logging.FileHandler(filename="log_receiver.txt")
console_handle = logging.StreamHandler()

logger.setLevel(logging.DEBUG)
logfile_handle.setLevel(logging.DEBUG)
console_handle.setLevel(logging.DEBUG)

log_format = logging.Formatter('%(name)s [%(levelname)s] :: %(asctime)s -> %(message)s')
console_handle.setFormatter(log_format)
logfile_handle.setFormatter(log_format)

logger.addHandler(logfile_handle)
logger.addHandler(console_handle)


## RTCP even port
data = []

# AUDIO VARIABLES
AUDIO_CHUNK_SIZE = 1024 # SAMPLES
AUDIO_CHANNELS = 2
AUDIO_FORMAT = pyaudio.paInt16 # 2 bytes size
AUDIO_BYTE_SIZE = 2
AUDIO_RATE = 44100
AUDIO_DELAY = (AUDIO_CHUNK_SIZE/AUDIO_RATE) * 16

# RTP VARIABLES
RTP_HEADER_SIZE = 12

# SOCKET VARIABLES
PORT_CTRL = 5004
PORT_TRANSMIT = 5005
PORT_SDP = 5006
SOCKET_CHUNK_SIZE = 1024 # SAMPLES
SOCKET_BROADCAST_SIZE = SOCKET_CHUNK_SIZE*AUDIO_CHANNELS*AUDIO_BYTE_SIZE + RTP_HEADER_SIZE# BYTES

class loginHandler(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        logger.debug("[LOGIN]\t\tStart Thread")
        self.stop_thread = False
        self.hostIP = ""
        self.sockUDP = None
        self.login = False

    def run(self):
        try:
            logger.debug("[LOGIN][UDP]\tOpen socket")
            self.sockUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sockUDP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sockUDP.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sockUDP.bind(("0.0.0.0", int(PORT_SDP)))
            self.sockUDP.settimeout(1)
            
            while True: 
                if self.stop_thread is True:
                    break

                logger.debug("[LOGIN]\t\tSend broadcast login request")
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
                    logger.info(f'[LOGIN]\t\tSuccessfull logged in to {self.hostIP}')
                    break
               
                time.sleep(2)
            logger.debug("[LOGIN]\t\tStop Thread")
            logger.debug("[LOGIN][UDP]\tclosing socket")
            self.sockUDP.close()
        except Exception as e:
            logger.debug("[LOGIN]\t\tStop Thread")
            logger.error(f"[LOGIN]\t\tException on run method {e}")
            logger.debug("[LOGIN][UDP]\tclosing socket")
            self.sockUDP.close()

class sessionHandler(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.stop_thread = False
        self.hostIP = ""
        self.STATE = 0 # 0 = logged out, 1 = logged in
        self.sockUDP = None
        self.sockTCP = None
        self.timer = 0
        self.active = False


    def run(self):
        try:
            while self.stop_thread is not True:
                if self.STATE == 0: # LOGGED OUT, try to LOGIN
                    logger.info("[SESSION][UDP]\tOpen socket")
                    self.sockUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                    self.sockUDP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self.sockUDP.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    self.sockUDP.bind(("0.0.0.0", int(PORT_SDP)))
                    self.sockUDP.settimeout(1)
                    
                    
                    while True:
                        if self.stop_thread is True:
                            break

                        logger.info("[SESSION]\tSend broadcast login request")
                        self.sockUDP.sendto(bytes("Login Request", "utf-8"), ("255.255.255.255", PORT_SDP))

                        try:
                            data, addr = self.sockUDP.recvfrom(1024)
                            data, addr = self.sockUDP.recvfrom(1024)
                        except socket.timeout:
                            pass

                        if(data == b'Login OK'):
                            self.hostIP = addr[0]
                            self.STATE = 1
                            self.timer = time.time()
                            self.active = True
                            logger.info(f'[SESSION]\tSuccessfull logged in to {self.hostIP}')
                            break
                        time.sleep(2)
                    logger.info("[SESSION][UDP]\tclosing socket")
                    self.sockUDP.close()

                if self.STATE == 1:
                    self.sockTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.sockTCP.bind(("0.0.0.0", PORT_CTRL))
                    self.sockTCP.listen(1)
                    self.sockTCP.settimeout(1)
                    logger.info("[SESSION][TCP]\tOpen socket")

                    while self.STATE == 1 and self.stop_thread is not True:
                        try:
                            conn, addr = self.sockTCP.accept()
                            logger.info("[SESSION][TCP]\tConnection opened")
                            try:
                                data = conn.recv(1024)
                                if(data == b'STATE'):
                                    logger.info(f"[SESSION]\tState is requested by {addr[0]}")
                                    logger.info("[SESSION]\tState is OK")
                                    conn.sendto(bytes("STATE OK", "utf-8"), (addr[0], PORT_CTRL))
                                    self.timer = time.time()
                            finally:
                                logger.info("[SESSION]\tConnection closed")
                                conn.close()
                        except socket.timeout:
                            pass
                        if(self.active == False):
                            self.STATE = 0
                            logger.info("[SESSION]\tNo incoming data")
                            logger.info("[SESSION][TCP]\tClose socket")
                            self.sockTCP.close()
                            break
                        if(time.time() - self.timer > 62):
                            self.STATE = 0
                            logger.info("[SESSION][TCP]\tClose socket")
                            self.sockTCP.close()
                            break

            if self.stop_thread is True :
                logger.info("[SESSION]\tThread is stopping")
                logger.info("[SESSION][TCP]\tClose socket")
                logger.info("[SESSION][UDP]\tClose socket")
                self.sockTCP.close()
                self.sockUDP.close()

        except Exception as e:
            logger.info(f'[SESSION]\tException in run method -> {e}')
            logger.info("[SESSION][TCP]\tClose socket")
            logger.info("[SESSION][UDP]\tClose socket")
            self.sockTCP.close()
            self.sockUDP.close()
               
class playAudio(threading.Thread):
    global data
    def __init__(self, delayBuffer=10):
        threading.Thread.__init__(self)
        logger.debug("[PLAY]\t\tStart Thread")
        self.stop_thread = False
        self.stream = None
        self.pa = None
        self.delayBuffer = delayBuffer
        self.init = False
        self.delayArray = []
        self.lastBuffer = time.time()

    def playBuffer(self):
        #print(round((time.time() - self.lastBuffer)*1000000.0, 2))
        self.stream.write(data[0].getPayload())
        del data[0]
        #time.sleep(0.001)
        self.lastBuffer = time.time()

    def run(self):
        try:
            self.pa = pyaudio.PyAudio()
            self.stream = self.pa.open(format=AUDIO_FORMAT, channels=AUDIO_CHANNELS, rate=AUDIO_RATE, output=True, frames_per_buffer=AUDIO_CHUNK_SIZE)
            logger.debug("[PLAY]\t\tStart audio stream")

            while True:
                if self.stop_thread is True:
                    break

                if len(data) == 0:
                    continue

                time_playout = float(data[0].ssrc()) + (float(data[0].timestamp())/1000000.0) + AUDIO_DELAY
                delay = time.time() - time_playout
                while(delay < -0.000005):
                    #time.sleep(0.0001)
                    # if(time.time() - self.timeDiff > 0.07 and self.init is True):
                    #     break
                    delay = time.time() - time_playout
                    if( time.time() - self.lastBuffer > 0.07 and self.init):
                        break

                self.delayArray.append(time.time() - time_playout)
                if len(self.delayArray) > self.delayBuffer:
                    del self.delayArray[0]

                self.playBuffer()

                if len(data) > 0:
                    self.playBuffer()

                if(self.delayArray[0] > 0 and len(data) > 0):
                    self.playBuffer()

                self.init = True
            logger.debug("[PLAY]\t\tStop Thread")
            logger.debug("[PLAY]\t\tStop audio stream")
            self.stream.close()
            self.pa.terminate()
        except Exception as e:
            logger.debug("[PLAY]\t\tStop Thread")
            logger.error(f"[PLAY]\t\tException from run method {e}")
            logger.debug("[PLAY]\t\tStop audio stream")
            self.stream.close()
            self.pa.terminate()

class receiveAudio(threading.Thread):
    global data
    def __init__(self, stats = True):
        threading.Thread.__init__(self)
        logger.debug("[RECEIVE]\t\tStart Thread")
        self.stop_thread = False
        self.sockUDP = None
        self.stats = stats
        if(self.stats):
            self.timerTotal = 0
            self.timer = 0
            self.packetRate = 0
            self.packetRateTotal = 0
            self.packetsReceived = 0
            self.packetsReceivedTotal = 0
            self.seqNum = None
            self.lostPackets = 0
            self.lostPacketsTotal = 0
            self.packetLoss = 0
            self.packetLossTotal = 0
            self.delayArray = []
            self.delayTimer = None


        self.incomingData = True
        self.timeouts = 0

    def run(self):
        try:
            logger.debug("[RECEIVE][UDP]\tOpen socket")
            self.sockUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sockUDP.bind(("0.0.0.0", int(PORT_TRANSMIT)))
            self.sockUDP.settimeout(1)
            
            if self.stats:
                self.timerTotal = time.time()
                self.timer = time.time()

            while True:
                # Stop the thread when variable is set through main program
                if self.stop_thread is True:
                    break

                # Stop the thread when there is no incoming Data
                if self.incomingData is False:
                    break

                # Set statistics
                if(time.time() - self.timer > 5.0 and self.stats):
                    self.packetsReceivedTotal = self.packetsReceivedTotal + self.packetsReceived
                    self.packetRate = round(self.packetsReceived*SOCKET_BROADCAST_SIZE*8/((time.time() - self.timer)*1000000.0), 2)
                    self.packetRateTotal = round(self.packetsReceivedTotal*SOCKET_BROADCAST_SIZE*8/((time.time() - self.timerTotal)*1000000.0), 2)
                    self.timer = time.time()
                    self.packetLoss = self.lostPackets / (self.lostPackets + self.packetsReceived)
                    self.lostPacketsTotal = self.lostPacketsTotal + self.lostPackets
                    self.packetLossTotal = self.lostPacketsTotal / (self.lostPacketsTotal + self.packetsReceivedTotal)
                    self.lostPackets = 0
                    self.packetsReceived = 0
                    #thread_play.stream.rate = 22050
                try:
                    new_data = self.sockUDP.recv(SOCKET_BROADCAST_SIZE)
                    if self.delayTimer is not None:
                        self.delayArray.append(time.time() - self.delayTimer)
                    if len(self.delayArray) > 100:
                        del self.delayArray[0]
                    self.delayTimer = time.time()
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(new_data)
                    data.append(rtpPacket)
                    # Set Statistics
                    if self.stats:
                        if self.seqNum == None:
                            self.seqNum = rtpPacket.seqNum() - 1
                        if rtpPacket.seqNum() != self.seqNum + 1:
                            self.lostPackets = self.lostPackets + 1
                        self.seqNum = rtpPacket.seqNum()
                        self.packetsReceived = self.packetsReceived + 1
                    time.sleep(0.001)
                except socket.timeout:
                    logger.debug("[RECEIVE]\t\tTimeout")
                    self.timeouts = self.timeouts + 1
                    
                    # Raise incomind data flag when more than 5 timeouts occur
                    if self.timeouts > 5:
                        self.incomingData = False


            # Stopping the thread
            logger.debug("[RECEIVE]\t\tStop Thread")
            logger.debug("[RECEIVE][UDP]\tClose socket")
            self.sockUDP.close()
        except Exception as e:
            logger.debug("[RECEIVE]\t\tStop Thread")
            logger.error(f"[RECEIVE]\t\tException from run method {e}")
            logger.debug("[RECEIVE][UDP]\tClose socket")
            self.sockUDP.close()

if __name__ == "__main__":
    thread_play = playAudio(delayBuffer=100)
    thread_play.start()
    LOGIN_STATE = False
    delay = []
    avg = 0
    try:
        while True:
            if LOGIN_STATE is False:
                thread_login = loginHandler()
                thread_login.start()
                thread_login.join()
                LOGIN_STATE = thread_login.login
                if LOGIN_STATE is True:

                    thread_receive = receiveAudio(stats=True)
                    thread_receive.start()
                continue

            LOGIN_STATE = thread_receive.incomingData
            time.sleep(2)
            if thread_play.init is True:        
                meanPlay = sum(thread_play.delayArray) / len(thread_play.delayArray)
                resPlay = sum((i - meanPlay) ** 2 for i in thread_play.delayArray) / len(thread_play.delayArray) 
                meanReceive = sum(thread_receive.delayArray) / len(thread_receive.delayArray)
                resReceive = sum((i - meanReceive) ** 2 for i in thread_receive.delayArray) / len(thread_receive.delayArray) 
                logger.info(f"Packets received: {thread_receive.packetsReceived} | Packet rate: {thread_receive.packetRate} Mb/s | Packet loss: {thread_receive.packetLoss} % | Total packets received: {thread_receive.packetsReceivedTotal} | Total packet rate: {thread_receive.packetRateTotal} Mb/s | Packet loss total: {thread_receive.packetLossTotal} %")
                logger.info(f"avg delay: {round(meanReceive*1000.0, 2)} us | var: {round(resReceive*1000.0, 2)} ms | min: {round(min(thread_receive.delayArray)*1000.0, 2)} us | max: {round(max(thread_receive.delayArray)*1000.0, 2)} us")
                logger.info(f"current delay: {round(thread_play.delayArray[-1]*1000000.0, 2)} us | avg: {round(meanPlay*1000000.0, 2)} us | var: {round(resPlay*1000000000000.0, 2)} ps | min: {round(min(thread_play.delayArray)*1000000.0, 2)} us | max: {round(max(thread_play.delayArray)*1000000.0, 2)} us")
        
    except KeyboardInterrupt:
        thread_login.stop_thread = True
        thread_play.stop_thread = True
        thread_receive.stop_thread = True

        
