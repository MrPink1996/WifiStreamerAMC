import wave
import pyaudio
import socket
from threading import Thread
import sys
import time
from configuration import configuration as conf
import queue

q = queue.Queue()

UDP_IP_HOST = conf.UDP_IP_HOST
UDP_IP_CLIENT_RASPIZERO = '192.168.178.20'
UDP_PORT = conf.UDP_PORT
SAMPLING_FREQUENCY = conf.SAMPLING_FREQUENCY
CHUNK_SIZE = conf.CHUNK_SIZE
BUFFER_SIZE = conf.BUFFER_SIZE


def audioInputIntern():
    p = pyaudio.PyAudio()
    # info = p.get_host_api_info_by_index(0)
    # numdevices = info.get('deviceCount')
    # for i in range(0, numdevices):
    #     if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
    #         print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))

    stream = p.open(format = pyaudio.paInt16,
                    channels = 2,
                    rate = SAMPLING_FREQUENCY,
                    input = True, input_device_index=2)
    
    while(True):
        q.put(stream.read(int(CHUNK_SIZE/4), exception_on_overflow=False))
    
def audio_stream():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    #udp.settimeout(0.2)
    
    while(True):
        if(not q.empty()):
            udp.sendto(q.get(), ('<broadcast>', UDP_PORT))
    udp.close()

if __name__ == '__main__':
    readInput = Thread(target=audioInputIntern, args=())
    sendAudio = Thread(target=audio_stream, args=())

    readInput.start()
    sendAudio.start()
    sendAudio.join()