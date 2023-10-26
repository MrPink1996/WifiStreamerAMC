import wave
import pyaudio
import socket
from threading import Thread
import sys
import time
from configuration import configuration as conf
import queue

UDP_IP_HOST = conf.UDP_IP_HOST
UDP_IP_CLIENT_RASPIZERO = '192.168.178.20'
UDP_PORT = conf.UDP_PORT
SAMPLING_FREQUENCY = conf.SAMPLING_FREQUENCY
CHUNK_SIZE = conf.CHUNK_SIZE


def audioInput():
    wf = wave.open("Teeinengland.wav", 'rb')
    data = []
    for i in range(wf.getnframes()):
        data.append(wf.readframes(int(CHUNK_SIZE/4)))
    return data
    
def audio_stream(data):
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp.settimeout(0.2)
    
    while(len(data) > 0):
        udp.sendto(data.pop(0), ('<broadcast>', UDP_PORT))
    udp.close()

if __name__ == '__main__':
    data = audioInput()
    print(len(data))
    audio_stream(data)