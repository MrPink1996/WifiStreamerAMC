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


def audioRecord():
    p = pyaudio.PyAudio()
    # info = p.get_host_api_info_by_index(0)
    # numdevices = info.get('deviceCount')
    # for i in range(0, numdevices):
    #     if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
    #         print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))

    stream = p.open(format = pyaudio.paInt16,
                    channels = 2,
                    rate = SAMPLING_FREQUENCY,
                    input = True, input_device_index=2, frames_per_buffer=CHUNK_SIZE)
    
    while(True):
        q.put(stream.read(CHUNK_SIZE, exception_on_overflow=False))
    
def audioStream():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while(True):
        udp.sendto(q.get(), ('192.168.178.83', UDP_PORT))
    udp.close()

def audioPlay():
    p = pyaudio.PyAudio()
    stream = p.open(format = pyaudio.paInt16,
                    channels = 2,
                    rate = SAMPLING_FREQUENCY,
                    output = True)

    # Play the sound by writing the audio data to the stream
    while(not q.empty()):
        stream.write(q.get())
    

    # Close and terminate the stream
    stream.close()
    p.terminate()

if __name__ == '__main__':
    recorder = Thread(target=audioRecord, args=())
    streamer = Thread(target=audioStream, args=())
    player = Thread(target=audioPlay, args=())
    recorder.daemon = True
    streamer.daemon = True

    recorder.start()
    time.sleep(2)
    streamer.start()
    recorder.join()
    streamer.join()
    print("finished streamer")