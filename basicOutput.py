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
                    output = True)


    # Play the sound by writing the audio data to the stream
    print("Queue size before playing out: ", q.qsize())
    while(True):
        if(not q.empty()):
            stream.write(q.get())

    # Close and terminate the stream
    stream.close()
    p.terminate()

def get_sound():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) # UDP
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", UDP_PORT))

    while (True):
        data, addr = sock.recvfrom(CHUNK_SIZE) # buffer size is 1024 bytes
        q.put(data)


if __name__ == "__main__":
    thread1 = Thread(target= get_sound, args=())

    thread2 = Thread(target= play_sound, args=())

    thread1.start()
    time.sleep(10)
    thread2.start()

    while(True):
        print("QUEUE SIZE:" , q.qsize())
        time.sleep(0.5)
    thread2.join()


    