import socket
from configuration import configuration as conf
import pyaudio
import wave
from threading import Thread
import time
import queue


q = queue.Queue()

UDP_IP_CLIENT = conf.UDP_IP_CLIENT
UDP_PORT = conf.UDP_PORT
SAMPLING_FREQUENCY = conf.SAMPLING_FREQUENCY
CHUNK_SIZE = conf.CHUNK_SIZE


def play_sound():
    p = pyaudio.PyAudio()
    stream = p.open(format = pyaudio.paInt16,
                    channels = 2,
                    rate = SAMPLING_FREQUENCY,
                    output = True, frames_per_buffer=CHUNK_SIZE)


    # Play the sound by writing the audio data to the stream
    while(True):
        stream.write(q.get(), CHUNK_SIZE)


def get_sound():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
    sock.bind(("192.168.178.83", UDP_PORT))

    while (True):
        data, addr = sock.recvfrom(CHUNK_SIZE*2*2) # buffer size is 1024 bytes
        q.put(data)

if __name__ == "__main__":
    thread1 = Thread(target= get_sound, args=())
    thread2 = Thread(target= play_sound, args=())
    thread1.daemon = True
    thread2.daemon = True
    thread1.start()
    thread2.start()
    thread2.join()
    thread1.join()
    