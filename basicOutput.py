import socket
from configuration import configuration as conf

UDP_IP = conf.UDP_IP
UDP_PORT = conf.UDP_PORT
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
sock.bind((UDP_IP, UDP_PORT))
while True:
   data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
   print("received message: %s" % data)