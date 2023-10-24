import wave
import pyaudio
import socket
from threading import Thread
import sys
import time
from configuration import configuration as conf

frames = []
UDP_IP_HOST = conf.UDP_IP_HOST
UDP_IP_CLIENT_RASPIZERO = '192.168.178.83'
UDP_PORT = conf.UDP_PORT
SAMPLING_FREQUENCY = conf.SAMPLING_FREQUENCY

def audioInput():
    wf = wave.open("Teeinengland.wav", 'rb')
    data = wf.readframes(wf.getnframes())
    return data
    

def audio_stream(data):
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind((UDP_IP_HOST, UDP_PORT))
    FRAMESIZE = 1472
    while(len(data) > FRAMESIZE):
        udp_packet = data[:FRAMESIZE]
        data = data[FRAMESIZE:]
        udp.sendto(udp_packet, (UDP_IP_CLIENT_RASPIZERO, UDP_PORT))
        time.sleep((FRAMESIZE / 4) / SAMPLING_FREQUENCY)

    udp.close()

if __name__ == '__main__':

    data = audioInput()
    #print(len(data))
    print(type(data), data[0:10])
    audio_stream(data)