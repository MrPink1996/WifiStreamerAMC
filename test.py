import pyaudio
import random
import time
data = [] # Stream of audio bytes 

# AUDIO VARIABLES
AUDIO_CHUNK_SIZE = 64 # SAMPLES
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
SOCKET_CHUNK_SIZE = 64 # SAMPLES
SOCKET_BROADCAST_SIZE = SOCKET_CHUNK_SIZE*AUDIO_CHANNELS*AUDIO_BYTE_SIZE # BYTES

# RTP VARIABLES
RTP_VERSION = 2
RTP_PADDING = 0
RTP_EXTENSION = 0
RTP_CC = 0
RTP_MARKER = 0
RTP_PT = 10


seqnum = random.randint(1, 9999)
ssrc = random.randint(1, 9999)
timeStart = time.time()
packetTime = (AUDIO_CHUNK_SIZE / AUDIO_RATE)
timestamp = (time.time() - timeStart) + 64 * packetTime

start = time.time()
counter = 0
def callback(in_data, frame_count, time_info, status):
    global start, counter
    counter = counter + 1
    if(counter == 5000):
        print((counter * frame_count) / (time.time() - start))
        counter = 0
        start = time.time()
    return (None, pyaudio.paContinue)

p = pyaudio.PyAudio()
stream = p.open(format=AUDIO_FORMAT, channels=AUDIO_CHANNELS, rate=AUDIO_RATE, input=True, frames_per_buffer=AUDIO_CHUNK_SIZE, input_device_index=1)
start = time.time()
while(True):
    data = stream.read(AUDIO_CHUNK_SIZE, exception_on_overflow=False)
    counter = counter + 1
    if(counter == 5000):
        print((counter * AUDIO_CHUNK_SIZE) / (time.time() - start))
        counter = 0
        start = time.time()