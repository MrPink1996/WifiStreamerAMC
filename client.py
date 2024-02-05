import pyaudio
import socket
import time
import threading
import random
import logging
import os
import scapy.contrib.igmp
from scapy.all import *


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
rtt = 0

OUTPUT_BUFFER_SIZE = 16
HEADER_SIZE = 10

# AUDIO VARIABLES
AUDIO_CHUNK_SIZE = 1024 # SAMPLES
AUDIO_CHANNELS = 2
AUDIO_FORMAT = pyaudio.paInt16 # 2 bytes size
AUDIO_BYTE_SIZE = 2
AUDIO_RATE = 44100
AUDIO_DELAY = (AUDIO_CHUNK_SIZE/AUDIO_RATE) * OUTPUT_BUFFER_SIZE

# SOCKET VARIABLES
SERVER_IP = ""
PORT_TRANSMIT = 5005
SOCKET_CHUNK_SIZE = 1024 # SAMPLES
SOCKET_BROADCAST_SIZE = SOCKET_CHUNK_SIZE*AUDIO_CHANNELS*AUDIO_BYTE_SIZE + HEADER_SIZE# BYTES
           
class playAudio(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        logger.debug("[PLAY]\t\tStart Thread")
        self.stop_thread = False
        self.stream = None
        self.pa = pyaudio.PyAudio()

    def byteToFloat32(self, byte):
        return float((byte[0] << 24) + (byte[1] << 16) + (byte[2] << 8) + (byte[3]))

    def run(self):
        global timeStart, data
        try:
            self.stream = self.pa.open(format=AUDIO_FORMAT, channels=AUDIO_CHANNELS, rate=AUDIO_RATE, output=True, frames_per_buffer=AUDIO_CHUNK_SIZE) # , output_device_index=3
            logger.debug("[PLAY]\t\tStart audio stream")

            while True:
                if self.stop_thread is True:
                    break

                if len(data) == 0:
                    continue
                
                # Get data from buffer and delete packet
                data_out = data[0]
                del data[0]

                # Calculate time for playout
                time_playout = ((self.byteToFloat32(data_out[4:8])) / 1000000.0) + AUDIO_DELAY

                # Calculate delay
                delay = (time.time() - timeStart) - time_playout
                
                # Wait for playout
                while(delay < 0.0):
                    delay = (time.time() - timeStart) - time_playout

                # Playout packet
                self.stream.write(data_out[HEADER_SIZE:])
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
        self.packetCount = 0

    def byteToFloat32(self, byte):
        return float((byte[0] << 24) + (byte[1] << 16) + (byte[2] << 8) + (byte[3]))

    def run(self):
        global data, SERVER_IP, rtt, timeStart
        try:
            logger.debug("[RECEIVE][UDP]\tOpen socket")
            self.sockUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sockUDP.bind(('224.3.29.71', int(PORT_TRANSMIT)))
            #group = socket.inet_aton('224.3.29.71')
            #mreq = struct.pack('4sL', group, socket.INADDR_ANY)
            mreq = b'\xe0\x03\x1dG\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            self.sockUDP.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            self.sockUDP.settimeout(3)

            while True:
                if self.stop_thread is True:
                    break

                try:
                    # Get new data from server
                    new_data, address = self.sockUDP.recvfrom(SOCKET_BROADCAST_SIZE)
                    self.packetCount = self.packetCount + 1
                    if len(new_data) != SOCKET_BROADCAST_SIZE:
                        continue
                    # Set Server ip
                    SERVER_IP = address[0]
                    
                    # Calculate sending time of packet
                    time_current = ((self.byteToFloat32(new_data[:4])) / 1000000.0) + rtt/2.0

                    # Calculate client time with round trip time
                    if timeStart == 0:
                        timeStart = time.time() - time_current
                    else:
                        d = (time.time() - timeStart) - time_current
                        timeStart = timeStart + (0.01 * d)

                    # Append data to processing buffer
                    data.append(new_data)
                    if len(data) > 2 * OUTPUT_BUFFER_SIZE:
                        del data[0]

                    # if self.packetCount > 400:
                    #     self.packetCount = 0
                    #     igmpPacket = IP(dst='224.3.29.71')/scapy.contrib.igmp.IGMP(type=0x16, gaddr="224.3.29.71", mrcode=20)
                    #     send(igmpPacket, verbose=False)

                except socket.timeout:
                    print("packet length", self.packetCount)
                    igmpPacket = IP(dst='224.3.29.71')/scapy.contrib.igmp.IGMP(type=0x16, gaddr="224.3.29.71", mrcode=20)
                    send(igmpPacket, verbose=False)
                    logger.debug("[RECEIVE]\t\tTimeout")
                    logger.debug(f"[RECEIVE]\t\tRestarted Socket")

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

    def ping(self, ip, n):
        response = os.popen(f"ping -c {n} {ip} ")
        data = response.read()
        data = data.split("\n")[-2]
        data = data.split("=")[-1][1:-3]
        data = data.split("/")
        rtt_avg = float(data[1]) / 1000.0
        return rtt_avg

    def run(self):
        global rtt, SERVER_IP

        # Wait till server ip is recognized
        while SERVER_IP == "":
            time.sleep(1)

        now = time.time() - 60
        while(True):
            if self.stop_thread is True:
                logger.debug("[SYNC]\t\tStop Thread")
                break

            # Every 60 seconds update round trip time
            if (time.time() - now > 60):
                now = time.time()
                rtt = self.ping(SERVER_IP, 10)
            
            time.sleep(1)


if __name__ == "__main__":
    # Start Receiving Audio
    thread_receive = receiveAudio()
    thread_receive.start()

    # Start Synchronizing
    thread_synchronize = synchronisationHandler()
    thread_synchronize.start()

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
