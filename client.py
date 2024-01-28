import pyaudio
import socket
from RtpPacket import RtpPacket
import time
import threading
import random
import logging
import struct

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
timeStart = 0

# AUDIO VARIABLES
AUDIO_CHUNK_SIZE = 1024 # SAMPLES
AUDIO_CHANNELS = 2
AUDIO_FORMAT = pyaudio.paInt16 # 2 bytes size
AUDIO_BYTE_SIZE = 2
AUDIO_RATE = 44100
AUDIO_DELAY = (AUDIO_CHUNK_SIZE/AUDIO_RATE) * 128


# SOCKET VARIABLES
SERVER_IP = ""
PORT_SYNC = 5003
PORT_CTRL = 5004
PORT_TRANSMIT = 5005
PORT_SDP = 5006
SOCKET_CHUNK_SIZE = 1024 # SAMPLES
SOCKET_BROADCAST_SIZE = SOCKET_CHUNK_SIZE*AUDIO_CHANNELS*AUDIO_BYTE_SIZE + 6# BYTES
           
class playAudio(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        logger.debug("[PLAY]\t\tStart Thread")
        self.stop_thread = False
        self.stream = None
        self.pa = pyaudio.PyAudio()
        self.init = False

    def run(self):
        global timeStart, data
        try:
            self.stream = self.pa.open(format=AUDIO_FORMAT, channels=AUDIO_CHANNELS, rate=AUDIO_RATE, output=True, frames_per_buffer=AUDIO_CHUNK_SIZE)
            logger.debug("[PLAY]\t\tStart audio stream")

            while True:
                if self.stop_thread is True:
                    break

                if len(data) == 0:
                    continue
                
                timestamp = (data[0][2] << 24) + (data[0][3] << 16) + (data[0][4] << 8) + (data[0][5])
                del data[0]
                time_playout = (float(timestamp)/1000000.0) + AUDIO_DELAY
                print(time_playout)
                delay = (time.time() - timeStart) - time_playout
                while(delay < 0.0):
                    delay = (time.time() - timeStart) - time_playout                
                self.stream.write(data[0].getPayload())
                del data[0]
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
    def __init__(self):
        threading.Thread.__init__(self)
        logger.debug("[RECEIVE]\t\tStart Thread")
        self.stop_thread = False
        self.sockUDP = None
        self.seqNum = None
        self.incomingData = True
        self.timeouts = 0

    def run(self):
        global data, SERVER_IP
        try:
            logger.debug("[RECEIVE][UDP]\tOpen socket")
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

                # Stop the thread when there is no incoming Data
                if self.incomingData is False:
                    break

                try:
                    new_data, address = self.sockUDP.recvfrom(SOCKET_BROADCAST_SIZE)
                    SERVER_IP = address[0]
                    data.append(new_data)
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

class synchronisationHandler(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        logger.debug("[SYNC]\t\tStart Thread")
        self.sock = None
        self.stop_thread = False
        self.init = False

    def run(self):
        global timeStart, SERVER_IP
        now = time.time() - 60
        self.delayArray = []
        while(True):
            time.sleep(1)
            if self.stop_thread is True:
                logger.debug("[SYNC]\t\tStop Thread")
                break
            if (time.time() - now > 60 ):
                now = time.time()
                for i in range(20):
                    try:
                        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.sock.connect((SERVER_IP, int(PORT_SYNC)))
                        timeSend = time.time()
                        self.sock.sendall(bytes(str("0"), "utf-8"))
                        data = self.sock.recv(1024)
                        timeReceive = time.time()
                        tt = (timeReceive - timeSend) / 2.0
                        timeServer = float(data.decode("utf-8")) + tt
                        timeClient = time.time() - timeStart
                        delay = timeServer - timeClient
                        self.delayArray.append(delay)
                    finally:
                        self.sock.close()
                mean = sum(self.delayArray) / len(self.delayArray)
                if( abs(mean) > 0.01):
                    timeStart = time.time() - (float(data.decode("utf-8")) + tt)
                    print(f"time delay: {mean}, set timer!")
                    self.init = True
                else:
                    timeStart = timeStart - ( 0.1 * mean )
                    print(f"time delay: {mean}, adjusted timer: {round((-0.1 * mean)*1000000.0, 4)} us")
                self.delayArray.clear()

if __name__ == "__main__":
    # Start Receiving Audio
    thread_receive = receiveAudio()
    thread_receive.start()

    # Wait for receiving Server ip address
    while SERVER_IP == "":
        time.sleep(0.5)

    # Start Synchronizing
    thread_synchronize = synchronisationHandler()
    thread_synchronize.start()

    # Wait for synchronizing is initialized    
    while thread_synchronize.init is False:
        time.sleep(0.5)

    # Start Playing Audio
    thread_play = playAudio()
    thread_play.start()


    # Main loop and display informations
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        thread_play.stop_thread = True
        thread_receive.stop_thread = True
        thread_synchronize.stop_thread = True

        
