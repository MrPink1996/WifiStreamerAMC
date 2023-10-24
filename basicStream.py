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

def udpStreamIn():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        if len(frames) > 0:
            data = frames.pop(0)
            udp.sendto(data,  (UDP_IP_HOST, UDP_PORT))
            time.sleep(CHUNK / SAMPLING_FREQUENCY)
    udp.close()


def record(stream, CHUNK):
    while True:
        frames.append(stream.read(CHUNK))

def audio_stream():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind((UDP_IP_HOST, UDP_PORT))
    CHUNK = 1024
    wf = wave.open("Teeinengland.wav", 'rb')
    
    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    input=True,
                    frames_per_buffer=CHUNK)
    
    print("Number of samples: ", wf.getnframes() * CHUNK)
    nbyteswritten = 0
    for i in range(500):
        data = wf.readframes(CHUNK)
        udp.sendto(data,  (UDP_IP_CLIENT_RASPIZERO, UDP_PORT))
        time.sleep(CHUNK / SAMPLING_FREQUENCY)
        nbyteswritten = nbyteswritten + len(data)
    print("Number bytes send: ", nbyteswritten)

    udp.close()

if __name__ == '__main__':
    CHUNK = 512
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100

    # p = pyaudio.PyAudio()
    # p = pyaudio.PyAudio()
    # info = p.get_host_api_info_by_index(0)
    # numdevices = info.get('deviceCount')

    # for i in range(0, numdevices):
    #     if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
    #         print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))
    # stream = p.open(format = FORMAT, channels = CHANNELS, rate = RATE,  input = True, frames_per_buffer = CHUNK , input_device_index=2)
    # Tr = Thread(target = record, args = (stream, CHUNK,))
    # Ts = Thread(target = udpStreamIn)
    thread = Thread(target= audio_stream, args=())
    thread.start()
    thread.join()
    # Tr.daemon = True
    # Ts.daemon = True
    # Tr.start()
    # Ts.start()
    # Tr.join()
    # Ts.join()