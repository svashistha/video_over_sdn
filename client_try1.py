
import socket
import time

def Main():
    host = '10.0.0.11'
    port = 8765

    s = socket.socket()
    s.connect((host, port))

    filename = raw_input("Filename? -> ")
    file_ext=filename.split('.')[-1]
    if filename != 'q':
        s.send(filename)
        data = s.recv(1024)
        if data[:6] == 'EXISTS':
            filesize = long(data[6:])
            message = raw_input("File exists, " + str(filesize) +"Bytes, download? (Y/N)? -> ")
            if message.upper() == 'Y':
                s.send("OK")
                startTime = s.recv(1024)
                f = open('new_file_from_client'+file_ext, 'wb')
                data = s.recv(1024)
                totalRecv = len(data)
                f.write(data)
                while totalRecv < filesize:
                    data = s.recv(1024)
                    totalRecv += len(data)
                    f.write(data)
                    print "{0:.2f}".format((totalRecv/float(filesize))*100)+ "% Done"                                                
                endTime = time.time()
                print endTime - float(startTime)                
                print "Download Complete!"            
                f.close()
        else:
            print "File Does Not Exist!"

    s.close()

if __name__ == '__main__':    
    Main()
