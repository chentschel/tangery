import time
import os
import re
import syslog

from stats import serverStats

# COMMANDS
COMMANDS = {
    'GET': "^get (.{1,250})\s*\r\n",
    'SET': "^set (.{1,250}) ([0-9]+) ([0-9]+) ([0-9]+)\r\n",
    'DEL': "^delete (.{1,250}) ([0-9]+)\r\n",
    'STA': "^(stats|stats (.{1,250}))\r\n"
}
for k, v in COMMANDS.items(): COMMANDS[k] = re.compile(v)

GET_RESPONSE       = "VALUE %s %s %s\r\n%s\r\nEND\r\n"
GET_RESPONSE_EMPTY = "END\r\n"

SET_RESPONSE_SUCCESS  = "STORED\r\n"
SET_RESPONSE_FAILURE  = "NOT STORED\r\n"

DELETE_RESPONSE_OK  = "DELETED\r\n"

STATS_RESPONSE      ="\
STAT pid %d\r\n\
STAT uptime %d\r\n\
STAT time %d\r\n\
STAT version %s\r\n\
STAT rusage_user %0.6f\r\n\
STAT rusage_system %0.6f\r\n\
STAT curr_items %d\r\n\
STAT total_items %d\r\n\
STAT bytes %d\r\n\
STAT curr_connections %d\r\n\
STAT total_connections %d\r\n\
STAT cmd_get %d\r\n\
STAT cmd_set %d\r\n\
STAT get_hits %d\r\n\
STAT get_misses %d\r\n\
STAT bytes_read %d\r\n\
STAT bytes_written %d\r\n\
STAT limit_maxbytes %d\r\n\
END\r\n"

STATS_KEY_RESPONSE  = "\
STAT queue_items %d\r\n\
STAT total_items %d\r\n\
STAT expired_items %d\r\n\
STAT logfile_size %d\r\n\
END\r\n"

# ERROR responses
ERR_BAD_CMD_LINE    = "CLIENT_ERROR bad command line format\r\n"
ERR_UNKNOWN_COMMAND = "ERROR\r\n"
ERR_SERVER_ERROR    = "SERVER_ERROR %s\r\n"

MAX_RELATIVE_EXPIRY_TIME = 60*60*24*30

class ClientHandler(object):

    dataBuffer  = ""
    bytesCount  = 0
    bytesRead   = 0

    def __init__(self, conn, queue_collection):
        self.connection = conn
        self.queues = queue_collection
        self.resetRequest()
        self.resetResponse()

    def canWrite(self):
        return not self.readState

    def canRead(self):
        return self.readState

    def handleRead(self):
        data = self.connection.recv(1024)
        if not data: 
            return False

        self.dataBuffer += data
        serverStats['bytes_read'] += len(data)

        if not self.dataHeader:
            h = self.dataBuffer.find('\r\n')
            if h < 0:
                return True if len(self.dataBuffer) < 512 else False

            h += 2
            self.dataHeader = self.dataBuffer[:h]
            self.dataBuffer = self.dataBuffer[h:]
            self.processHeader()

        else:
            self.bytesRead += len(data)
            self.processPayload()
    
        return True

    def resetRequest(self):
        self.dataHeader = ''
        self.bytesRead = 0

    def resetResponse(self):
        self.readState = True
        self.writeBuff = ''

    def processHeader(self):        
        if self.dataHeader.startswith('set'):
            match = COMMANDS['SET'].match(self.dataHeader)
            if match:
                self.prepareSET(match.group(1), match.group(2),
                                match.group(3), match.group(4))
                return
            else:   
                self.writeResponse(ERR_BAD_CMD_LINE)
        
        elif self.dataHeader.startswith('get'):
            match = COMMANDS['GET'].match(self.dataHeader)
            if match: 
                self.processGet(match.group(1).strip())
            else:
                self.writeResponse(ERR_BAD_CMD_LINE)

        elif self.dataHeader.startswith('delete'):
            match = COMMANDS['DEL'].match(self.dataHeader)
            if match:
                self.processDelete(match.group(1))
            else: 
                self.writeResponse(ERR_BAD_CMD_LINE)

        elif self.dataHeader.startswith('stats'):
            match = COMMANDS['STA'].match(self.dataHeader)
            if match:
                self.processStats(match.group(2))
            else:
                self.writeResponse(ERR_BAD_CMD_LINE)
        else:
            syslog.syslog("ERROR: Unknown command")
            self.writeResponse(ERR_UNKNOWN_COMMAND)
        
        self.resetRequest()

    def prepareSET(self, key, flags, expiry, bytes):
        self.bytesCount = int(bytes) + 2
        self.stash = (key, flags, expiry)

        if self.dataBuffer:
            self.bytesRead += len(self.dataBuffer)
            self.processPayload()

    def processPayload(self):
        if self.bytesRead < self.bytesCount:
            return

        key, flags, expiry = self.stash
        data = self.dataBuffer[:self.bytesCount - 2]

        #Check if its offset from now or absolute unix time.
        expiry = int(expiry)
        if expiry and expiry < MAX_RELATIVE_EXPIRY_TIME:
            expiry = time.time() + int(expiry)
    
        self.queues.put(key, (flags, expiry, data))

        # If we had another header after body \r\n
        # have to make sure we dont delete it.
        self.dataBuffer = self.dataBuffer[self.bytesCount:]        

        self.resetRequest()
        self.writeResponse(SET_RESPONSE_SUCCESS)

    def processGet(self, key):
        now = time.time()

        flags, expiry, data = self.queues.get(key)
        while data:
            if expiry == 0 or expiry >= now:
                break
            #Count expired on queue.
            self.queues.getQueue(key).expired_items += 1

            flags, expiry, data = self.queues.get(key)

        if data:
            self.writeResponse(GET_RESPONSE % (key, flags, len(data), data))
        else:
            self.writeResponse(GET_RESPONSE_EMPTY)

        self.resetRequest()

    def processDelete(self, key):
        self.queues.delete(key)
        self.writeResponse(DELETE_RESPONSE_OK)

    def writeResponse(self, response):
        self.writeBuff = response
        self.readState = False

    def handleWrite(self):
        written = self.connection.send(self.writeBuff)
        self.writeBuff = self.writeBuff[written:]

        if not self.writeBuff:
            self.readState = True

        serverStats['bytes_written'] += written

        return True

    def handleClose(self):
        self.connection.close()
        del self.connection
    
    def __queueStats(self, key):
        queue = self.queues.getQueue(key)
        if queue is not None:
            return STATS_KEY_RESPONSE % (
                len(queue),
                queue.total_items,
                queue.expired_items,
                queue.logsize
            )
        return ERR_SERVER_ERROR % "key not found"

    def __serverStats(self):
        return STATS_RESPONSE % (
            serverStats['server_pid'],
            time.time() - serverStats['start_time'],
            time.time(),
            serverStats['server_version'],
            os.times()[0], #user time
            os.times()[1], #system time
            self.queues.countItems(),
            serverStats['total_items'],
            serverStats['current_bytes'],
            serverStats['connections'],
            serverStats['total_connections'],
            serverStats['get_requests'],
            serverStats['set_requests'],
            serverStats['get_hits'],
            serverStats['get_misses'],
            serverStats['bytes_read'],
            serverStats['bytes_written'],
            0 # LIMIT MAX BYTES 
        )

    def processStats(self, key):
        stats = self.__queueStats(key) if key else self.__serverStats()
        self.writeResponse(stats)

