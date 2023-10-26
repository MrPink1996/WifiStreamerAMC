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


def audioRecord(stop = False, stop_buffer=1000):
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

        if(stop and stop_buffer < q.qsize()):
            break
    
def audioStream():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    #udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    #udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    #udp.settimeout(0.2)
    
    while(not q.empty()):
        buffer = q.get()
        udp.sendto(buffer, ('192.168.178.83', UDP_PORT))
        time.sleep(0.01)
        print("send on packet with length ", len(buffer))
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
    recorder = Thread(target=audioRecord, args=(True, 1000))
    streamer = Thread(target=audioStream, args=())
    player = Thread(target=audioPlay, args=())

    recorder.start()
    recorder.join()
    print("finished recoder thread with ", q.qsize(), " loaded frames")
    time.sleep(2)
    # player.start()
    # player.join()
    print("finished player thread")
    streamer.start()
    streamer.join()
    print("finished streamer")