import time
import pyaudio
import socket
import random
import threading
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
PORT_TRANSMIT = 5005
LIST_OF_HOSTS = []#["192.168.178.172", "192.168.178.102"]
SOCKET_CHUNK_SIZE = 1024 # SAMPLES
SOCKET_BROADCAST_SIZE = SOCKET_CHUNK_SIZE*AUDIO_CHANNELS*AUDIO_BYTE_SIZE # BYTES


class transmitAudio(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        logger.info("[TRANSMIT]\tStart thread")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        ttl = struct.pack('b', 1)
        print(ttl, type(ttl))
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        self.stop_thread = False

    def run(self):
        global data
        try:
            logger.info("[TRANSMIT]\tStart transmitting audio")
            while True:
                if self.stop_thread is True:
                    break

                if len(data) == 0:
                    continue
                
                # Get Packet from buffer and delete packet from buffer
                out_data = data[0]
                del data[0]

                # Send message to multicast group
                self.sock.sendto(out_data, ('224.3.29.71', int(PORT_TRANSMIT)))

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
    def __init__(self):
        threading.Thread.__init__(self)
        logger.info("[RECORD]\t\tStart Thread")
        self.p = None
        self.stream = None
        self.seqnum = random.randint(1, 99)
        self.stop_thread = False
        self.timeStart = 0
        self.adcCorrection = 0
    
    def callback(self, in_data, frame_count, time_info, status):
        global data

        # Add adc correction because of different timingstructures
        if(self.adcCorrection == 0):
            self.adcCorrection = time_info['input_buffer_adc_time'] - time.time()

        # Increment sequence Number
        self.seqnum = self.seqnum + 1

        # Calculate timestamp of record time
        timestamp = ((time_info['input_buffer_adc_time'] - self.adcCorrection)) - self.timeStart

        # Create packet for transmission and add to buffer
        header = bytearray(6)
        header[0] = (self.seqnum >> 8) & 255
        header[1] = (self.seqnum) & 255
        header[2] = (int(timestamp * 1000000.0) >> 24 ) & 255
        header[3] = (int(timestamp * 1000000.0) >> 16 ) & 255
        header[4] = (int(timestamp * 1000000.0) >> 8 ) & 255
        header[5] = (int(timestamp * 1000000.0)) & 255
        packet = header + in_data
        data.append(packet)

        # Delete packets when buffer is full
        if(len(data) >= 16):
            del data[0]
        return (None, pyaudio.paContinue)
    
    def run(self):
        try:
            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(format=AUDIO_FORMAT, channels=AUDIO_CHANNELS, rate=AUDIO_RATE, input=True, frames_per_buffer=AUDIO_CHUNK_SIZE, stream_callback=self.callback, input_device_index=0)
            self.stream.start_stream()
            logger.info("[RECORD]\t\tStart audio stream")
            while self.stop_thread is not True:
                time.sleep(0.5)
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
                if self.stop_thread is True:
                    break
                try:
                    connection, client_address = self.sock.accept()
                    data = connection.recv(1024)
                    connection.sendall(bytes(str(time.time() - self.timeStart), "utf-8"))
                except socket.timeout:
                    pass
                except Exception as e:
                    break
            logger.info(f"[SYNC]\t\tStop Thread")
            self.sock.close()
            logger.info("[SYNC][TCP]\tClose socket")
        except Exception as e:
            logger.info(f"[SYNC]\t\tException from run method: {e}")
            self.sock.close()


if __name__ == "__main__":
    thread_synchronize = synchronisationHandler()
    thread_synchronize.start()

    thread_recording = recordAudio()
    thread_recording.start()

    thread_transmit = transmitAudio()
    thread_transmit.start()

    try:
        while True:
            time.sleep(1)
        
    except KeyboardInterrupt:
        thread_recording.stop_thread = True
        thread_transmit.stop_thread = True
        thread_synchronize.stop_thread = True
