from panda3d.core import *
from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from direct.directnotify import DirectNotifyGlobal

from otpr.base.OTPRTypes import *

from Client import *
from ClientAccountManager import *

class ClientAgent(QueuedConnectionManager):
    serverAddress = config.GetString("ca-address", "127.0.0.1")
    serverPort = config.GetInt("ca-port", 7101)
    mdAddress = config.GetString("md-address", "127.0.0.1")
    mdPort = config.GetInt("md-port", 6667)
    serverVersion = config.GetString("server-version", "no-version-set")
    hashVal = 0
    
    notify = DirectNotifyGlobal.directNotify.newCategory("ClientAgent")

    def __init__(self):
        QueuedConnectionManager.__init__(self)
        self.accountManager = ClientAccountManager()
        self.allocator = UniqueIdAllocator(1100, 1500)
        self.allocatedChannels = []
        self.connectionToClientObj = {}
        self.connectionToChannel = {}
    
    def startup(self):
        self.ourChannel = CLIENT_AGENT_CHANNEL
        self.listener = QueuedConnectionListener(self, 0)
        self.reader = QueuedConnectionReader(self, 0)
        self.reader2 = QueuedConnectionReader(self, 0)
        self.writer = ConnectionWriter(self, 0)
        self.__openConnection()
        self.__runConnection()
        self.notify.info("Started up")
        
    def __openConnection(self):
        self.tcpSocket = self.openTCPServerRendezvous(self.serverPort, 1000)
        if self.tcpSocket:
            self.listener.addConnection(self.tcpSocket)
            
            taskMgr.add(self. __listenerPool, "listener-pool")
            taskMgr.add(self. __readerPool, "reader-pool")
            
    def __listenerPool(self, task):
        if self.listener.newConnectionAvailable():
            rendezvous = PointerToConnection()
            netAddress = NetAddress()
            newConnection = PointerToConnection()
            
            if self.listener.getNewConnection(rendezvous, netAddress, newConnection):
                newConnection = newConnection.p()
                self.setupNewConnectionChannel(newConnection)
                self.reader.addConnection(newConnection)
    
        return task.cont
        
    def setupNewConnectionChannel(self, connection):
        newClientChannel = self.allocateNewChannel()
        newClient = Client(self, connection, newClientChannel)
        self.connectionToClientObj[connection] = newClient
        self.connectionToChannel[connection] = newClientChannel
        self.registerForChannel(newClientChannel)
            
    def allocateNewChannel(self):
        channelAllocated = self.allocator.allocate()
        self.allocatedChannels.append(channelAllocated)
        return channelAllocated
        
    def registerForChannel(self, channel):
        datagram = PyDatagram()
        datagram.addServerHeader(channel, channel, CONTROL_SET_CHANNEL)
        self.writer.send(datagram, self.tcpConn)
        
    def unregisterForChannel(self, channel):
        datagram = PyDatagram()
        datagram.addServerHeader(channel, channel, CONTROL_REMOVE_CHANNEL)
        self.writer.send(datagram, self.tcpConn)
        
    def removeChannel(self, channel):
        self.allocator.free(channel)
        if channel in self.allocatedChannels:
            self.allocatedChannels.remove(channel)
        self.unregisterForChannel(channel)
        
    def __readerPool(self, task):
        if self.reader.dataAvailable():
            datagram = NetDatagram()
            if self.reader.getData(datagram):
                conn = datagram.getConnection()
                if conn in self.connectionToClientObj:
                    if __live__:
                        try:
                            self.connectionToClientObj[conn].handleMessage(datagram)
                        except:
                            self.closeConnection(CLIENT_DISCONNECT_TRUNCATED_DATAGRAM, "Truncated datagram", self.connection)
                    else:
                        self.connectionToClientObj[conn].handleMessage(datagram)
                else:
                    self.notify.warning("Unexpected datagram from unknown client %s / %s" %(msg_type, str(self.connection)))
        
        return task.cont
        
    def handleDatagram(self, dg):
        connection = dg.getConnection()
        di = PyDatagramIterator(dg)
        msgType = di.getUint16()
        
        if msgType == CLIENT_DISCONNECT:
            self.removeConnectionInstance(connection)
        else:
            self.notify.warning("Recieved an unexpected internal datagram: %s from: %s" % (msg_type, str(self.connection)))
            
    def __handleClientHeartbeat(self, connection, di):
        self.connectionToClientObj[connection].heartbeat()                
    
    def closeConnection(self, code, reason, connection):
        datagram = PyDatagram()
        datagram.addUint16(CLIENT_GO_GET_LOST)
        datagram.addUint16(int(code))
        datagram.addString(str(reason))
        self.writer.send(datagram, connection)
        self.removeConnectionInstance(connection)
        
    def removeConnectionInstance(self, connection):
        if connection in self.connectionToClientObj:
            self.connectionToClientObj[connection].getLost()
            self.reader.removeConnection(connection)
            del self.connectionToClientObj[connection]
    
    def __runConnection(self):
        self.tcpConn = self.openTCPClientConnection(self.mdAddress, self.mdPort, 3000)
        if self.tcpConn:
			self.registerForChannel(self.ourChannel)
			self.reader2.addConnection(self.tcpConn)

			taskMgr.add(self.__readerPoolReciever, "task reader reciever")
            
    def __readerPoolReciever(self, task):
        if self.reader2.dataAvailable():
            datagram = NetDatagram()
			
            if self.reader2.getData(datagram):
                self.__handleDatagramReciever(datagram)

        return task.cont
            
    def __handleDatagramReciever(self, dg):
        connection = datagram.getConnection()
        if not connection:
            return
        
        di = PyDatagramIterator(dg)
        recieverChannel = di.getUint64()
        senderChannel = di.getUint64()
        msgType = di.getUint16()
        print msg_type

            
            
            
            
            
            