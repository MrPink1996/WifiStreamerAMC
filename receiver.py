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

logger.setLevel(logging.INFO)
logfile_handle.setLevel(logging.INFO)
console_handle.setLevel(logging.INFO)

log_format = logging.Formatter('%(name)s [%(levelname)s] :: %(asctime)s -> %(message)s')
console_handle.setFormatter(log_format)
logfile_handle.setFormatter(log_format)

logger.addHandler(logfile_handle)
logger.addHandler(console_handle)


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
        logger.info("[LOGIN]\t\tStart Thread")
        self.stop_thread = False
        self.hostIP = ""
        self.sockUDP = None
        self.login = False

    def run(self):
        try:
            logger.info("[LOGIN][UDP]\tOpen socket")
            self.sockUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sockUDP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sockUDP.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sockUDP.bind(("0.0.0.0", int(PORT_SDP)))
            self.sockUDP.settimeout(1)
            
            while True: 
                if self.stop_thread is True:
                    break

                logger.info("[LOGIN]\t\tSend broadcast login request")
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
            logger.info("[LOGIN]\t\tStop Thread")
            logger.info("[LOGIN][UDP]\tclosing socket")
            self.sockUDP.close()
        except Exception as e:
            logger.info("[LOGIN]\t\tStop Thread")
            logger.info(f"[LOGIN]\t\tException on run method {e}")
            logger.info("[LOGIN][UDP]\tclosing socket")
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
    def __init__(self):
        threading.Thread.__init__(self)
        logger.info("[PLAY]\t\tStart Thread")
        self.stop_thread = False
        self.stream = None
        self.pa = None
        self.delay = 0
        self.init = False

    def run(self):
        try:
            self.pa = pyaudio.PyAudio()
            self.stream = self.pa.open(format=AUDIO_FORMAT, channels=AUDIO_CHANNELS, rate=AUDIO_RATE, output=True, frames_per_buffer=AUDIO_CHUNK_SIZE)
            logger.info("[PLAY]\t\tStart audio stream")

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

            logger.info("[PLAY]\t\tStop Thread")
            logger.info("[PLAY]\t\tStop audio stream")
            self.stream.close()
            self.pa.terminate()
        except Exception as e:
            logger.info("[PLAY]\t\tStop Thread")
            logger.info(f"[PLAY]\t\tException from run method {e}")
            logger.info("[PLAY]\t\tStop audio stream")
            self.stream.close()
            self.pa.terminate()

class receiveAudio(threading.Thread):
    global data
    def __init__(self):
        threading.Thread.__init__(self)
        logger.info("[RECEIVE]\t\tStart Thread")
        self.stop_thread = False
        self.sockUDP = None

        self.timerTotal = 0
        self.timer = 0
        self.packetRate = 0
        self.packetRateTotal = 0
        self.packets = 0
        self.packetsTotal = 0


        self.incomingData = True
        self.timeouts = 0

    def run(self):
        try:
            logger.info("[RECEIVE][UDP]\tOpen socket")
            self.sockUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sockUDP.bind(("0.0.0.0", int(PORT_TRANSMIT)))
            self.sockUDP.settimeout(1)
            self.timerTotal = time.time()
            self.timmer = time.time()
            while True:
                if self.stop_thread is True:
                    break
                
                if self.incomingData is False:
                    break


                if(time.time() - self.timer > 5.0):
                    self.packetsTotal = self.packetsTotal + self.packets
                    self.packetRate = round(self.packets*SOCKET_BROADCAST_SIZE*8/((time.time() - self.timer)*1000000.0), 2)
                    self.packetRateTotal = round(self.packetsTotal*SOCKET_BROADCAST_SIZE*8/((time.time() - self.timerTotal)*1000000.0), 2)
                    self.packets = 0
                    self.timer = time.time() 
                    
                try:
                    new_data = self.sockUDP.recv(SOCKET_BROADCAST_SIZE)
                    incomingData = True
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(new_data)
                    data.append(rtpPacket)
                    self.packets = self.packets + 1

                except socket.timeout:
                    logger.info("[RECEIVE]\t\tTimeout")
                    self.timeouts = self.timeouts + 1
                    
                    if self.timeouts > 5:
                        self.incomingData = False

                time.sleep(0.01)

            # Stopping the thread
            logger.info("[RECEIVE]\t\tStop Thread")
            logger.info("[RECEIVE][UDP]\tClose socket")
            self.sockUDP.close()
        except Exception as e:
            logger.info("[RECEIVE]\t\tStop Thread")
            logger.info(f"[RECEIVE]\t\tException from run method {e}")
            logger.info("[RECEIVE][UDP]\tClose socket")
            self.sockUDP.close()

if __name__ == "__main__":

    thread_play = playAudio()
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

                    thread_receive = receiveAudio()
                    thread_receive.start()
                continue

            LOGIN_STATE = thread_receive.incomingData
            time.sleep(2)
            if thread_play.init is True:
                logger.info(f"Packets received: {thread_receive.packets} | Packet rate: {thread_receive.packetRate} Mb/s | Total packets received {thread_receive.packetsTotal} | Total packet rate {thread_receive.packetRateTotal} Mb/s | Current audio Delay: {thread_play.delay*1000000.0} us")
                delay.append(thread_play.delay)
                if len(delay) > 100:
                    del delay[0]
                mean = sum(delay) / len(delay)
                res = sum((i - mean) ** 2 for i in delay) / len(delay) 
                logger.info(f"avg: {round(mean*1000000.0, 2)} us | {round(res*1000000000000.0, 2)} ps | {round(min(delay)*1000000.0, 2)} us | {round(max(delay)*1000000.0, 2)} us")

        
    except KeyboardInterrupt:
        thread_login.stop_thread = True
        thread_play.stop_thread = True
        thread_receive.stop_thread = True

    print(delay)
        