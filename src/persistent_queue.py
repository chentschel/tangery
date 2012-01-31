import os
import cPickle
import syslog

from collections import deque

LOG_SOFT_MAX_SIZE = 16 * (1024**2) #Queue will wait to rotate until is empty after 16MB

CMD_APPEND  = 0x00
CMD_POPLEFT = 0x01

class PersistentQueue(deque):

    total_items = long()
    expired_items = long()

    def __init__(self, qname):
        deque.__init__(self)

        self.qname = qname
        self.openLog()

        self.initialBytes = self.__replayTransactions()  

    def append(self, data, transaction = True):
        if transaction: 
            self.transaction((CMD_APPEND, data))

        self.total_items += 1
        super(PersistentQueue, self).append(data)

    def popleft(self):
        self.transaction((CMD_POPLEFT, None))
        return super(PersistentQueue, self).popleft()

    def clear(self):
        super(PersistentQueue, self).clear()
        self.rotateLog()

    def closeLog(self):
        self.logfile.close()
        self.logfile = None

    def openLog(self):
        self.logfile = open(self.qname, 'a+')
        self.logsize = os.fstat(self.logfile.fileno()).st_size
    
    def rotateLog(self):
        self.closeLog()
        os.rename(self.qname, '%s.old' % self.qname)
        self.openLog()

    def __replayTransactions(self):
        bytes_read = 0
        try:
            syslog.syslog("Reading back transaction log for [%s]" % self.qname)
            while True:
                opCode, data = cPickle.load(self.logfile)
                if opCode == CMD_APPEND:
                    self.append(data, transaction = False)
                    bytes_read += len(data)

                elif opCode == CMD_POPLEFT:
                    try:
                        data = super(PersistentQueue, self).popleft()
                        bytes_read -= len(data)
                    except IndexError:
                        syslog.syslog("WARNING: CMD pop on empty queue: [%s]" % self.qname)

                else:
                    syslog.syslog("ERROR: invalid opCode '%s' on [%s]" % (opCode, self.qname))

        except cPickle.UnpicklingError, e:
            syslog.syslog("ERROR: %s" % e.message)
        except EOFError:
            syslog.syslog("Transaction log for [%s] done" % self.qname)

        return bytes_read

    def transaction(self, data):
        if not self.logfile:
            syslog.syslog("ERROR: No transation logfile avaliable [%s]" % self.qname)
            raise "No transaction logfile."
        
        #@TODO: HAVE TO MAKE THIS ASYNC OR NON-BLOCKING IO.
        cPickle.dump(data, self.logfile, -1)
        self.logsize += sum(map(len, data))

        if self.logsize > LOG_SOFT_MAX_SIZE and len(self) == 0:
            self.rotateLog()
