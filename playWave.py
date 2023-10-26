import wave
from configuration import configuration as conf
import pyaudio
import queue

SAMPLING_FREQUENCY = conf.SAMPLING_FREQUENCY
CHUNK_SIZE = conf.CHUNK_SIZE
BUFFER_SIZE = conf.BUFFER_SIZE
q = queue.Queue()

if __name__ == "__main__":
    wf = wave.open("Teeinengland.wav", 'rb')
    print(wf.getnframes())
    for i in range( int(wf.getnframes() / (CHUNK_SIZE / 4))):
        q.put(wf.readframes(int(CHUNK_SIZE/4)))
    wf.close()
    
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