import pyaudio
import socket
from RtpPacket import RtpPacket
import time
import threading
import random
import logging


# Configurations for console and file logger
# Configurations for console and file logger
logger = logging.getLogger("RTP Audio Handler")
logfile_handle = logging.FileHandler(filename="log.txt")
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
AUDIO_DELAY = 5

# RTP VARIABLES
RTP_HEADER_SIZE = 12

# SOCKET VARIABLES
PORT_CTRL = 5004
PORT_TRANSMIT = 5005
SOCKET_CHUNK_SIZE = 4096 # SAMPLES
SOCKET_BROADCAST_SIZE = SOCKET_CHUNK_SIZE*AUDIO_CHANNELS*AUDIO_BYTE_SIZE + RTP_HEADER_SIZE# BYTES

totalPackets = 0

def receive_session():
    global data, totalPackets
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    #sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("0.0.0.0", int(PORT_TRANSMIT)))
    logger.info(f'Socket bind succeed "0.0.0.0"')
    rtpPacket = RtpPacket()
    try:
        packets = 0
        now2 = time.time()
        now = time.time()
        while True:
            new_data = sock.recv(SOCKET_BROADCAST_SIZE)
            rtpPacket = RtpPacket()
            rtpPacket.decode(new_data)
            data.append(rtpPacket)
            packets = packets + 1
            if( time.time() - now > 30.0):
                totalPackets = totalPackets + packets
                logger.info(f"current {packets} packets | current rate {round(packets*SOCKET_BROADCAST_SIZE*8/((time.time() - now)*1000000), 2)} Mb/s | remaining packet: {len(data)} | total {totalPackets} packets | total rate {round(totalPackets*SOCKET_BROADCAST_SIZE*8/((time.time() - now2)*1000000), 2)} Mb/s")
                now = time.time()
                packets = 0
            time.sleep(0.001)
    except Exception as e:
        logger.info(e)
        logger.info('\nClosing socket and stream...')
        sock.close()

def play_session_blocking():
    global data
    try:
        p = pyaudio.PyAudio()
        stream = p.open(format=AUDIO_FORMAT, channels=AUDIO_CHANNELS, rate=AUDIO_RATE, output=True, frames_per_buffer=AUDIO_CHUNK_SIZE)
        now = time.time()

        while(True):
            # not enough packets to playout
            if( len(data) == 0):
                continue

            time_playout = float(data[0].ssrc()) + (float(data[0].timestamp())/1000000.0) + AUDIO_DELAY
            delay = time.time() - time_playout
            # playout is too fast, skip some packets
            if(delay > 0.0001):
                data = data[1:]
                continue

            # playout is too early, wait small random time
            if(delay < - 0.0001):
                time.sleep(random.random() * 0.0001)
                continue

            # playout packet
            stream.write(data[0].getPayload())
            data = data[1:]

            # print out informations every 30 seconds
            if(time.time() - now > 30.0):
                now = time.time()
                logger.info(f"playout time: {round(time_playout, 2)} | current time: {round(time.time(), 2)} | delay: {round(delay*1000000.0, 2)} us | remaining packets: {len(data)}")

            
    except Exception as e:
        logger.info(e)
        logger.info('\nClosing socket and stream...')
        stream.stop_stream()
        stream.close()
        p.terminate()
    
def ctrl_session():
    try:
        logger.info("Start controll session")
        now = time.time()
        while(True):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)  # UDP
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            logger.info("Send: I want to play music")
            sock.sendto(bytes("I want to play music", "utf-8"), ("255.255.255.255", PORT_CTRL))
            sock.close()
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Stop controll session")
        sock.close()

thread_receive = threading.Thread(target=receive_session, args=())
thread_play = threading.Thread(target=play_session_blocking, args=())
thread_ctrl = threading.Thread(target=ctrl_session, args=())

thread_ctrl.start()
thread_play.start()
thread_receive.start()
thread_receive.join()