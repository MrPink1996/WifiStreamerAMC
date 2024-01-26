import time
import pyaudio
import socket
import random
from RtpPacket import RtpPacket
import threading
import sys
import struct
import wave 

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
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        ttl = struct.pack('b', 1)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        self.stop_thread = False
        self.sendingTimes = []
        self.scriptFinished = False
        self.sleepVal = AUDIO_CHUNK_SIZE / AUDIO_RATE - 0.01
        self.sleepVals = []
        self.seqnum = random.randint(1, 9999)
        self.ssrc = random.randint(1, 9999)

    def run(self):
        
        wf = wave.open("Teeinengland.wav", 'rb')
        data = []
        while len(a := wf.readframes(1024)):
            self.seqnum = self.seqnum + 1
            rtpPacket = RtpPacket()
            rtpPacket.encode(RTP_VERSION, RTP_PADDING, RTP_EXTENSION, RTP_CC, self.seqnum, RTP_MARKER, RTP_PT, self.ssrc, 0, a)
            data.append(rtpPacket)
        try:
            counter = 0
            while True:                
                if self.stop_thread is True:
                    break
                out_data = data[counter].getPacket()
                counter = ( counter + 1 ) % len(data)
                self.sock.sendto(out_data, ('224.3.29.71', int(PORT_TRANSMIT)))
                self.sendingTimes.append(time.time())

                if len(self.sendingTimes) > 10000:
                    print("sending times reached limit")
                    break

                if len(self.sendingTimes) > 1:
                    lastDelay = self.sendingTimes[-1] - self.sendingTimes[-2]
                    self.sleepVal = self.sleepVal + ((AUDIO_CHUNK_SIZE / AUDIO_RATE) - lastDelay)*0.01
                time.sleep(self.sleepVal)


            
            self.sock.close()
        except Exception as e:
            self.sock.close()

        f = open("test.txt", "w")
        for item in self.sendingTimes:
            f.write(str(item) + "\n")

        print("written successfull: ", len(self.sendingTimes))

        


class recordAudio(threading.Thread):
    def __init__(self, timeStart):
        threading.Thread.__init__(self)
        self.p = None
        self.stream = None
        self.seqnum = random.randint(1, 9999)
        self.ssrc = random.randint(1, 9999)
        self.stop_thread = False
        self.timeStart = timeStart
        self.packetTime = (AUDIO_CHUNK_SIZE / AUDIO_RATE)
        self.adcCorrection = 0
        self.packetDelta = []
        self.startTime = 0
    
    def callback(self, in_data, frame_count, time_info, status):
        global data
        if(self.adcCorrection == 0):
            self.adcCorrection = time_info['input_buffer_adc_time'] - time.time()
            self.startTime = time.time()
        self.seqnum = self.seqnum + 1
        rtpPacket = RtpPacket()
        timestamp = ((time_info['input_buffer_adc_time'] - self.adcCorrection)) - self.timeStart
        rtpPacket.encode(RTP_VERSION, RTP_PADDING, RTP_EXTENSION, RTP_CC, self.seqnum, RTP_MARKER, RTP_PT, self.ssrc, timestamp, in_data)
        data.append(rtpPacket)
        return (None, pyaudio.paContinue)
    
    def run(self):
        try:
            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(format=AUDIO_FORMAT, channels=AUDIO_CHANNELS, rate=AUDIO_RATE, input=True, frames_per_buffer=AUDIO_CHUNK_SIZE, stream_callback=self.callback, input_device_index=1)
            self.stream.start_stream()
            while self.stop_thread is not True:
                time.sleep(0.1)
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()
        except Exception as e:
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()


if __name__ == "__main__":
    print("start transmitting")
    thread_transmit = transmitAudio()
    thread_transmit.start()

    while True:
        time.sleep(1)
        print(thread_transmit.sleepVal)#, sum(thread_transmit.sleepVals) / len(thread_transmit.sleepVals), max(thread_transmit.sleepVals), min(thread_transmit.sleepVals))
