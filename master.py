import time
import pyaudio
import socket
import random
import threading
import logging
import struct


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
timeStart = time.time()

# AUDIO VARIABLES
AUDIO_CHUNK_SIZE = 1024 # SAMPLES
AUDIO_CHANNELS = 2
AUDIO_FORMAT = pyaudio.paInt16 # 2 bytes size
AUDIO_BYTE_SIZE = 2
AUDIO_DELAY = 5
AUDIO_RATE = 44100
AUDIO_MAX_BUFFER_SIZE = AUDIO_RATE * AUDIO_CHANNELS * AUDIO_BYTE_SIZE #BYTES

# SOCKET VARIABLES
PORT_TRANSMIT = 5005
SOCKET_CHUNK_SIZE = 1024 # SAMPLES
SOCKET_BROADCAST_SIZE = SOCKET_CHUNK_SIZE*AUDIO_CHANNELS*AUDIO_BYTE_SIZE # BYTES


class transmitAudio(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        logger.info("[TRANSMIT]\tStart thread")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, b'\x01')
        self.stop_thread = False

    def num2Bytes32(self, num):
        return bytes([(num >> 24 ) & 255, (num >> 16 ) & 255, (num >> 8 ) & 255, (num >> 0 ) & 255])

    def run(self):
        global data, timeStart
        try:
            logger.info("[TRANSMIT]\tStart transmitting audio")
            while True:
                if self.stop_thread is True:
                    break

                if len(data) == 0:
                    time.sleep(0.001)
                    continue
                
                # Get Packet from buffer and delete packet from buffer
                out_data = data[0]
                del data[0]
            
                # Send message to multicast group
                self.sock.sendto(self.num2Bytes32(int( (time.time() - timeStart) * 1000000.0)) + out_data, ('224.3.29.71', int(PORT_TRANSMIT)))
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
    def __init__(self):
        threading.Thread.__init__(self)
        logger.info("[RECORD]\t\tStart Thread")
        self.p = None
        self.stream = None
        self.seqnum = random.randint(1, 99)
        self.stop_thread = False

    def num2Bytes32(self, num):
        return bytes([(num >> 24 ) & 255, (num >> 16 ) & 255, (num >> 8 ) & 255, (num >> 0 ) & 255])
    
    def num2Bytes16(self, num):
        return bytes([(num >> 8 ) & 255, (num >> 0 ) & 255])
    
    def callback(self, in_data, frame_count, time_info, status):
        global data, timeStart

        # Increment sequence Number
        self.seqnum = self.seqnum + 1

        # Calculate timestamp of record time
        timestamp = time.time() - timeStart

        # Create packet for transmission and add to buffer
        packet = bytes(self.num2Bytes32(int(timestamp * 1000000.0) )) + bytes(self.num2Bytes16(self.seqnum)) + in_data
        data.append(packet)

        # Delete packets when buffer is full
        if(len(data) >= 16):
            del data[0]
        return (None, pyaudio.paContinue)
    
    def run(self):
        try:
            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(format=AUDIO_FORMAT, channels=AUDIO_CHANNELS, rate=AUDIO_RATE, input=True, frames_per_buffer=AUDIO_CHUNK_SIZE, stream_callback=self.callback, input_device_index=13)
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

if __name__ == "__main__":
    thread_recording = recordAudio()
    thread_recording.start()

    thread_transmit = transmitAudio()
    thread_transmit.start()

    try:
        while True:
            time.sleep(2)
        
    except KeyboardInterrupt:
        thread_recording.stop_thread = True
        thread_transmit.stop_thread = True
