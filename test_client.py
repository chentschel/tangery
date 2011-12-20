import thread
import socket
import time

HOST = '127.0.0.1'
PORT = 22122

start = time.time()

def producer(s, val):
    data = 'set key 0 0 10\r\n1234567890\r\n'
    ldata = len(data)
 
    for i in xrange(10000):
        l = s.send(data)
        if l < ldata:
            print "[P] - Can not send. Sent l: %s" % l

        r = s.recv(512)
        #print '[PROD]: %s' % r

    print "[P] - done. Total time: %s" % (time.time() - start)

def consumer(s, val):
    data = 'get key\r\n'
    ldata = len(data)

    for i in xrange(10000):
        l = s.send(data)
        if l < ldata:
            print "[C] - Can not send. Sent l: %s" % l

        r = s.recv(512)
        #print '[CONS]: %s' % r

    print "[C] done. Total time: %s" % (time.time() - start)

def main():
    for i in xrange(10):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))

        thread.start_new_thread(producer, (s, None))

    for i in xrange(11):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))

        thread.start_new_thread(consumer, (s, None))

    time.sleep(600)

if __name__ == "__main__":
    main()
