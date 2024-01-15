import time
import pyaudio
import socket
import random
from RtpPacket import RtpPacket
import threading
import sys
import logging
import struct

# Configurations for console and file logger
# Configurations for console and file logger
logger = logging.getLogger("RTP Audio Master")
logfile_handle = logging.FileHandler(filename="log_transmitter.txt")
console_handle = logging.StreamHandler()

logger.setLevel(logging.INFO)
logfile_handle.setLevel(logging.INFO)
console_handle.setLevel(logging.INFO)

log_format = logging.Formatter('%(name)s [%(levelname)s] :: %(asctime)s -> %(message)s')
console_handle.setFormatter(log_format)
logfile_handle.setFormatter(log_format)

logger.addHandler(logfile_handle)
logger.addHandler(console_handle)

data = [] # Stream of audio bytes 

# AUDIO VARIABLES
AUDIO_CHUNK_SIZE = 1024 # SAMPLES
AUDIO_CHANNELS = 2
AUDIO_FORMAT = pyaudio.paInt16 # 2 bytes size
AUDIO_BYTE_SIZE = 2
AUDIO_DELAY = 5
AUDIO_RATE = 44100
AUDIO_MAX_BUFFER_SIZE = AUDIO_RATE * AUDIO_CHANNELS * AUDIO_BYTE_SIZE #BYTES

# SOCKET VARIABLES
PORT_SYNC = 5003
PORT_CTRL = 5004
PORT_TRANSMIT = 5005
PORT_SDP = 5006
LIST_OF_HOSTS = []#["192.168.178.172", "192.168.178.102"]
SOCKET_CHUNK_SIZE = 1024 # SAMPLES
SOCKET_BROADCAST_SIZE = SOCKET_CHUNK_SIZE*AUDIO_CHANNELS*AUDIO_BYTE_SIZE # BYTES

# RTP VARIABLES
RTP_VERSION = 2
RTP_PADDING = 0
RTP_EXTENSION = 0
RTP_CC = 0
RTP_MARKER = 0
RTP_PT = 10

class transmitAudio(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        logger.info("[TRANSMIT]\tStart thread")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        ttl = struct.pack('b', 1)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        self.stop_thread = False

        self.timerTotal = 0
        self.timer = 0
        self.packetRate = 0
        self.packetRateTotal = 0
        self.packets = 0
        self.packetsTotal = 0

    def run(self):
        global data
        try:
            logger.info("[TRANSMIT]\tStart transmitting audio")
            self.timerTotal = time.time()
            self.timer = time.time()
            while True:
                if self.stop_thread is True:
                    break

                if len(data) == 0:
                    continue

                out_data = data[0].getPacket()
                del data[0]
                #print(out_data)
                self.sock.sendto(out_data, ('224.3.29.71', int(PORT_TRANSMIT)))
                self.packets = self.packets + 1
                if time.time() - self.timer > 5.0:
                    self.packetsTotal = self.packetsTotal + self.packets
                    self.packetRate = round(self.packets*SOCKET_BROADCAST_SIZE*8/((time.time() - self.timer)*1000000.0), 2)
                    self.packetRateTotal = round(self.packetsTotal*SOCKET_BROADCAST_SIZE*8/((time.time() - self.timerTotal)*1000000.0), 2)
                    self.packets = 0
                    self.timer = time.time()
                time.sleep(0.001)

            logger.info("[TRANSMIT]\tStop transmitting audio")
            logger.info("[TRANSMIT]\tStop Thread")
            logger.info("[TRANSMIT][UDP]\tClose socket")
            self.sock.close()
        except Exception as e:
            logger.info("[TRANSMIT]\tStop transmitting audio")
            logger.info(f"[TRANSMIT]\tException from run method {e}")
            logger.info("[TRANSMIT][UDP]\tClose socket")
            self.sock.close()

class recordAudio(threading.Thread):
    def __init__(self, timeStart):
        threading.Thread.__init__(self)
        logger.info("[RECORD]\t\tStart Thread")
        self.p = None
        self.stream = None
        self.seqnum = random.randint(1, 9999)
        self.ssrc = random.randint(1, 9999)
        self.stop_thread = False
        self.timeStart = timeStart
        self.packetTime = (AUDIO_CHUNK_SIZE / AUDIO_RATE)
        self.adcCorrection = 0
    
    def callback(self, in_data, frame_count, time_info, status):
        global data
        if(self.adcCorrection == 0):
            self.adcCorrection = time_info['input_buffer_adc_time'] - time.time()
        self.seqnum = self.seqnum + 1
        rtpPacket = RtpPacket()
        timestamp = ((time_info['input_buffer_adc_time'] - self.adcCorrection)) - self.timeStart        
        rtpPacket.encode(RTP_VERSION, RTP_PADDING, RTP_EXTENSION, RTP_CC, self.seqnum, RTP_MARKER, RTP_PT, self.ssrc, timestamp, in_data)
        data.append(rtpPacket)
        if(len(data) >= 16):
            del data[0]
        return (None, pyaudio.paContinue)
    
    def run(self):
        try:
            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(format=AUDIO_FORMAT, channels=AUDIO_CHANNELS, rate=AUDIO_RATE, input=True, frames_per_buffer=AUDIO_CHUNK_SIZE, stream_callback=self.callback, input_device_index=1)
            self.stream.start_stream()
            logger.info("[RECORD]\t\tStart audio stream")
            while self.stop_thread is not True:
                time.sleep(0.1)
            logger.info("[RECORD]\t\tStop Thread")
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()
        except Exception as e:
            logger.info(f"[RECORD]\t\tException from run method {e}")
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()

class synchronisationHandler(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        logger.info("[SYNC]\t\tStart Thread")
        self.sock = None
        self.stop_thread = False
        self.timeStart = time.time()

    def run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind(("0.0.0.0", int(PORT_SYNC)))
            logger.info("[SYNC][TCP]\tOpen socket")
            self.sock.listen(1)
            self.sock.settimeout(1)

            while(True):
                try:
                    connection, client_address = self.sock.accept()
                    data = connection.recv(1024)
                    connection.sendall(bytes(str(time.time() - self.timeStart), "utf-8"))
                except socket.timeout:
                    pass
                except Exception as e:
                    logger.info(f"[SYNC]\t\tException from run method: {e}")
                    self.sock.close()
                    logger.info("[SYNC][TCP]\tClose socket")
                    break
                if self.stop_thread is True:
                    logger.info(f"[SYNC]\t\tStop Thread")
                    self.sock.close()
                    logger.info("[SYNC][TCP]\tClose socket")
        except Exception as e:
            logger.info(f"[SYNC]\t\tException from run method: {e}")
            self.sock.close()


if __name__ == "__main__":
    thread_synchronize = synchronisationHandler()
    thread_synchronize.start()
    time.sleep(1)

    thread_recording = recordAudio(thread_synchronize.timeStart)
    thread_recording.start()

    thread_transmit = transmitAudio()
    thread_transmit.start()

    try:
        while True:
            time.sleep(5)
            if thread_transmit.packets > 0:
                logger.info(f"Time: {time.time() - thread_synchronize.timeStart} Packets send: {thread_transmit.packets} | Packet rate: {thread_transmit.packetRate} Mb/s | Total packets send {thread_transmit.packetsTotal} | Total packet rate {thread_transmit.packetRateTotal} Mb/s")
               
        
    except KeyboardInterrupt:
        thread_recording.stop_thread = True
        thread_transmit.stop_thread = True
        thread_synchronize.stop_thread = True
