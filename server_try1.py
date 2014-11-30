
import socket
import threading
import os
import time
import sys

def RetrFile(name, sock):
    filename = sock.recv(1024)
    if os.path.isfile(filename):
        sock.send("EXISTS " + str(os.path.getsize(filename)))
        userResponse = sock.recv(1024)
        if userResponse[:2] == 'OK':
            startTime = str(time.time())
            sock.send(startTime)            
            with open(filename, 'rb') as f:                    
                bytesToSend = f.read(1024)
                sock.send(bytesToSend)
                while bytesToSend != "":
                    bytesToSend = f.read(1024)
                    sock.send(bytesToSend)                
    else:
        sock.send("ERR ")

def Main():
    host = '10.0.0.11'
    port = 8765


    s = socket.socket()
    s.bind((host,port))

    s.listen(5)

    print "Server Started."
    while True:
        c, addr = s.accept()
        print "client connedted ip:<" + str(addr) + ">"
        t = threading.Thread(target=RetrFile, args=("RetrThread", c))
        t.start()
         
    s.close()

if __name__ == '__main__':    
    Main()

