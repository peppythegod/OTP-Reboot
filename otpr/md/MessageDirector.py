from panda3d.core import *

from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from direct.directnotify import DirectNotifyGlobal

from otpr.base.OTPRTypes import *
from MDParticipant import *

class MessageDirector(QueuedConnectionManager):
    serverAddress = config.GetString("md-address", "127.0.0.1")
    serverPort = config.GetInt("md-port", 7101)
    
    notify = DirectNotifyGlobal.directNotify.newCategory("MessageDirector")

    def __init__(self):
        QueuedConnectionManager.__init__(self)
        self.parkedConnections = []
        self.registeredParticipants = {}
        self.registeredClients = []
    
    def startup(self):
        self.listener = QueuedConnectionListener(self, 0)
        self.reader = QueuedConnectionReader(self, 0)
        self.writer = ConnectionWriter(self, 0)
        self.__openConnection()
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
                self.parkedConnections.append(newConnection)
                self.reader.addConnection(newConnection)
        
        return task.cont
                
    def __readerPool(self, task):
        if self.reader.dataAvailable():
            datagram = NetDatagram()
            if self.reader.getData(datagram):
                self.__handleDatagram(datagram)
        
        return task.cont
        
    def __handleDatagram(self, dg):
        connection = dg.getConnection()
        if not connection:
            self.dumpInvalidConnection(connection)
        
        di = PyDatagramIterator(dg)
        if di.getUint8() == 1:
            self.handleIncoming(di, connection, dg)
            
    def handleIncoming(self, di, connection, datagram):
        recieverChannel = di.getUint64()
        senderChannel = di.getUint64()
        messageType = di.getUint16() 
        
        if messageType == CONTROL_MESSAGE:
            self.routeMessage(di, datagram, recieverChannel, senderChannel)
        elif messageType == CONTROL_SET_CHANNEL:
            self.registerChannel(connection, recieverChannel)
        elif messageType == CONTROL_REMOVE_CHANNEL:
            self.unregisterChannel(connection, recieverChannel)
        
    def dumpInvalidConnection(self, connection):
        if connection in self.parkedConnections:
            self.reader.removeConnection(connection)
            del self.parkedConnections[connection]
            
    def routeMessage(self, di, datagram, recieverChannel, senderChannel): 
        if recieverChannel in self.registeredParticipants:
            dg = PyDatagram()
            dg.addUint64(recieverChannel)
            dg.addUint64(senderChannel)
            dg.addUint16(di.getUint16())
            dg.appendData(di.getRemainingBytes())
            self.writer.send(dg, self.registeredParticipants[recieverChannel])
            dg.clear()
        else:
            self.notify.warning("Route message from untrusted channel %d" % channel)
        
    def registerChannel(self, connection, channel):
        if self.authenticateChannel(connection, channel) == False:
            self.registeredParticipants[channel] = connection
            self.notify.debug("Registered channel: %d" % channel)
            new_client = MDParticipant(connection, channel)
            self.registeredClients.append(new_client)
        
        
    def authenticateChannel(self, connection, channel):
        if channel in self.registeredParticipants:
            if self.registeredParticipants[channel] == connection:
                for parked in self.parkedConnections:
                    if parked == connection:
                        self.parkedConnections.remove(connection)
                        return True
        else:
            return False
            
    def unregisterChannel(self, connection, channel):
        if self.authenticateChannel(connection, channel) == True:
            del self.registeredParticipants[channel]
            self.notify.debug("Un-Registered channel: %d" % channel)
            for client in self.registeredClients:
                if client.channel == channel:
                    self.registeredClients.remove(client)
        
        
        
        