import socket
from configuration import configuration as conf
import pyaudio
import wave
from threading import Thread
import time

UDP_IP_CLIENT = conf.UDP_IP_CLIENT
UDP_PORT = conf.UDP_PORT
SAMPLING_FREQUENCY = conf.SAMPLING_FREQUENCY

frames = []

def play_sound():
    global frames

    p = pyaudio.PyAudio()
    stream = p.open(format = pyaudio.paInt16,
                    channels = 2,
                    rate = SAMPLING_FREQUENCY,
                    output = True, )


    # Play the sound by writing the audio data to the stream
    while(len(frames) < 512):
        time.sleep(0.1)
    
    while(len(frames) > 0):
        stream.write(frames[:512])
        frames = frames[512:]

    # Close and terminate the stream
    stream.close()
    p.terminate()

def get_sound():
    global frames
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
    sock.bind((UDP_IP_CLIENT, UDP_PORT))
    while True:
        data, addr = sock.recvfrom(1472) # buffer size is 1024 bytes
        frames.append(data[:])





if __name__ == "__main__":

    thread1 = Thread(target= get_sound, args=())
    thread2 = Thread(target=play_sound, args=())

    thread1.start()
    thread2.start()
    thread2.join()
    thread1.join()
