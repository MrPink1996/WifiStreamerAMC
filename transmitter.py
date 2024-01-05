import time
import pyaudio
import socket
import random
from RtpPacket import RtpPacket
import threading
import sys
import logging


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
AUDIO_CHUNK_SIZE = 2048 # SAMPLES
AUDIO_CHANNELS = 2
AUDIO_FORMAT = pyaudio.paInt16 # 2 bytes size
AUDIO_BYTE_SIZE = 2
AUDIO_DELAY = 5
AUDIO_RATE = 44100
AUDIO_MAX_BUFFER_SIZE = AUDIO_RATE * AUDIO_CHANNELS * AUDIO_BYTE_SIZE #BYTES

# SOCKET VARIABLES
PORT_CTRL = 5004
PORT_TRANSMIT = 5005
PORT_SDP = 5006
LIST_OF_HOSTS = []#["192.168.178.172", "192.168.178.102"]
SOCKET_CHUNK_SIZE = 2048 # SAMPLES
SOCKET_BROADCAST_SIZE = SOCKET_CHUNK_SIZE*AUDIO_CHANNELS*AUDIO_BYTE_SIZE # BYTES

# RTP VARIABLES
RTP_VERSION = 2
RTP_PADDING = 0
RTP_EXTENSION = 0
RTP_CC = 0
RTP_MARKER = 0
RTP_PT = 10



class loginHandler(threading.Thread):
    global LIST_OF_HOSTS
    def __init__(self):
        threading.Thread.__init__(self)
        logger.info("[LOGIN]\t\tStart Thread")
        self.sockUDP = None
        self.stop_thread = False

    def run(self):
        try:
            logger.info("[LOGIN][UDP]\tOpen socket")
            self.sockUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sockUDP.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sockUDP.bind(("0.0.0.0", PORT_SDP))
            self.sockUDP.settimeout(1)
            while True:
                try:
                    data, addr = self.sockUDP.recvfrom(1024)
                    if data == b'LOGIN':
                        logger.info(f"[LOGIN]\t\tReceived login request from {addr[0]}")
                        logger.info(f"[LOGIN]\t\tAccept login")
                        self.sockUDP.sendto(bytes("OK", "utf-8"), (addr[0], PORT_SDP))
                        if addr[0] not in LIST_OF_HOSTS:
                            LIST_OF_HOSTS.append(addr[0])
                            logger.info(f"[LOGIN]\t\tAdd {addr[0]} to list of Hosts")
                        
                except socket.timeout:
                    pass
                if self.stop_thread is True:
                    break
            logger.info("[LOGIN]\t\tStop Thread")
            logger.info("[LOGIN][UDP]\tClose socket")
            self.sockUDP.close()
        except Exception as e:
            logger.info("[LOGIN]\t\tStop Thread")
            logger.info(f"[LOGIN]\t\tException in run method {e}")
            logger.info("[LOGIN][UDP]\tClose socket")
            self.sockUDP.close()

class senssionHandler(threading.Thread):
    global LIST_OF_HOSTS
    def __init__(self):
        threading.Thread.__init__(self)
        self.sock = None
        self.stop_thread = False

    def run(self):
        now = time.time()
        while self.stop_thread is not True:
            if(time.time() - now > 60.0):
                now = time.time()
                for host in LIST_OF_HOSTS:
                    try:
                        logger.info("[SESSION][TCP]\tOpen socket")
                        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        self.sock.connect((host, PORT_CTRL))
                        logger.info(f"[SESSION]\tRequest State from {host}")
                        self.sock.sendto(bytes("STATE", "utf-8"), (host, PORT_CTRL))
                        data = self.sock.recv(1024)
                        if( data == b'STATE OK'):
                            logger.info(f"[SESSION]\t{host} is active")
                        logger.info("[SESSION][TCP]\tClose socket")
                        self.sock.close()
                    except ConnectionRefusedError:
                        logger.info(f"[SESSION]\t{host} is not active")
                        LIST_OF_HOSTS.remove(host)
                        logger.info(f"[SESSION]\tDelete {host} from list of hosts")
                        logger.info("[SESSION][TCP]\tClose socket")
                        self.sock.close()
                    except Exception as e:
                        logger.info(f"[SESSION]\tException in run method {e}")
                        logger.info("[SESSION][TCP]\tClose socket")
                        self.sock.close()
            time.sleep(1)

class transmitAudio(threading.Thread):
    global data, LIST_OF_HOSTS
    def __init__(self):
        threading.Thread.__init__(self)
        logger.info("[TRANSMIT]\tStart thread")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.stop_thread = False

        self.timerTotal = 0
        self.timer = 0
        self.packetRate = 0
        self.packetRateTotal = 0
        self.packets = 0
        self.packetsTotal = 0

    def run(self):
        try:
            while(len(data) == 0 and len(LIST_OF_HOSTS) == 0):
                time.sleep(0.2)
            logger.info("[TRANSMIT]\tStart transmitting audio")
            self.timerTotal = time.time()
            self.timer = time.time()
            while True:
                if self.stop_thread is True:
                    break

                if len(LIST_OF_HOSTS) == 0:
                    self.timerTotal = time.time()
                    self.timer = time.time()
                    continue

                if len(data) == 0:
                    continue

                out_data = data[0].getPacket()
                #print(out_data[100:110])
                #print(time.time(), data[0].timestamp(), data[0].ssrc(), data[0].timestamp()/1000000.0, data[0].ssrc() + data[0].timestamp()/1000000.0)
                del data[0]
                #print(out_data)
                for host in LIST_OF_HOSTS:
                    self.sock.sendto(out_data, (host, int(PORT_TRANSMIT)))
                self.packets = self.packets + 1
                if time.time() - self.timer > 5.0:
                    self.packetsTotal = self.packetsTotal + self.packets
                    self.packetRate = round(self.packets*SOCKET_BROADCAST_SIZE*8/((time.time() - self.timer)*1000000.0), 2)
                    self.packetRateTotal = round(self.packetsTotal*SOCKET_BROADCAST_SIZE*8/((time.time() - self.timerTotal)*1000000.0), 2)
                    self.packets = 0
                    self.timer = time.time()
                time.sleep(0.01)

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
    global data
    def __init__(self):
        threading.Thread.__init__(self)
        logger.info("[RECORD]\t\tStart Thread")
        self.p = pyaudio.PyAudio()
        self.seqnum = random.randint(1, 9999)
        self.ssrc = int(time.time())
        self.stop_thread = False
        data.clear()
    
    def callback(self, in_data, frame_count, time_info, status):
        self.seqnum = self.seqnum + 1
        rtpPacket = RtpPacket()
        #rtpPacket.encode(RTP_VERSION, RTP_PADDING, RTP_EXTENSION, RTP_CC, self.seqnum, RTP_MARKER, RTP_PT, self.ssrc, time_info['input_buffer_adc_time'], in_data)
        rtpPacket.encode(RTP_VERSION, RTP_PADDING, RTP_EXTENSION, RTP_CC, self.seqnum, RTP_MARKER, RTP_PT, self.ssrc, time.time(), in_data)
        #print(time_info, time.time())
        data.append(rtpPacket)
        if(len(data) >= 10):
            del data[0]
        return (None, pyaudio.paContinue)

    def start_stream(self):
        info = self.p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range(0, numdevices):
            if (self.p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                print("Input Device id ", i, " - ", self.p.get_device_info_by_host_api_device_index(0, i).get('name'))
        self.stream = self.p.open(format=AUDIO_FORMAT, channels=AUDIO_CHANNELS, rate=AUDIO_RATE, input=True, frames_per_buffer=AUDIO_CHUNK_SIZE, stream_callback=self.callback, input_device_index=1)
        self.stream.start_stream()
        logger.info("[RECORD]\t\tStart audio stream")

    def stop_stream(self):
        data.clear()
        self.stream.stop_stream()
        self.stream.close()
        logger.info("[RECORD]\t\tStop audio stream")

    def restart_stream(self):
        self.stop_stream()
        data.clear()
        self.start_stream()

    def run(self):
        try:
            self.start_stream()
            while self.stop_thread is not True:
                time.sleep(0.5)
            logger.info("[RECORD]\t\tStop Thread")
            self.stop_stream()
            self.p.terminate()
        except Exception as e:
            logger.info(f"[RECORD]\t\tException from run method {e}")
            self.stop_stream()
            self.p.terminate()

if __name__ == "__main__":
    thread_login = loginHandler()
    thread_login.start()

    thread_recording = recordAudio()
    thread_recording.start()

    thread_transmit = transmitAudio()
    thread_transmit.start()

    try:
        while True:
            time.sleep(5)
            if thread_transmit.packets > 0 and len(LIST_OF_HOSTS) > 0:
               logger.info(f"Packets send: {thread_transmit.packets} | Packet rate: {thread_transmit.packetRate} Mb/s | Total packets send {thread_transmit.packetsTotal} | Total packet rate {thread_transmit.packetRateTotal} Mb/s")
        
    except KeyboardInterrupt:
        thread_login.stop_thread = True
        thread_recording.stop_thread = True
        thread_transmit.stop_thread = True
