import socket
from configuration import configuration as conf
import pyaudio
import wave
from threading import Thread
import time

UDP_IP_CLIENT = conf.UDP_IP_CLIENT
UDP_PORT = conf.UDP_PORT

frames = []

def play_sound():
    global frames
    filename = 'Teeinengland.wav'

    # Set chunk size of 1024 samples per data frame
    chunk = 1024  

    # Open the sound file 
    wf = wave.open(filename, 'rb')

    # Create an interface to PortAudio
    p = pyaudio.PyAudio()

    # Open a .Stream object to write the WAV file to
    # 'output = True' indicates that the sound will be played rather than recorded
    stream = p.open(format = p.get_format_from_width(wf.getsampwidth()),
                    channels = wf.getnchannels(),
                    rate = wf.getframerate(),
                    output = True)


    # Play the sound by writing the audio data to the stream
    time.sleep(3)
    while len(frames) > 0:
        stream.write(frames.pop(0))

    # Close and terminate the stream
    stream.close()
    p.terminate()

def get_sound():
    global frames
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
    sock.bind((UDP_IP_CLIENT, UDP_PORT))
    while True:
        data, addr = sock.recvfrom(4 * 1024) # buffer size is 1024 bytes
        frames.append(data)
   #print("received message: %s" % data)





if __name__ == "__main__":

    thread1 = Thread(target= get_sound, args=())
    thread2 = Thread(target=play_sound, args=())

    thread1.start()
    thread2.start()
    thread2.join()
    thread1.join()
