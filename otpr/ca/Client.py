from otpr.base.OTPRTypes import *

class Client:
    heartbeatInterval = config.GetDouble('heartbeat-interval', 15)
    
    def __init__(self, agent, connection, channel):
        self.agent = agent
        self.connection = connection
        self.channel = channel
        self.hbTaskName = str(self.connection) + "-heartbeatend"
        
    def heartbeat(self):
        if taskMgr.hasTaskNamed(self.hbTaskName):
            taskMgr.remove(self.hbTaskName)
        taskMgr.doMethodLater(self.heartbeatInterval, self.__closeConnection, self.hbTaskName)
        
    def __closeConnection(self, task):
        self.drop(122, "The client hasn't responded with a heartbeat within the past 15 seconds!")
                            
        return task.done
        
    def getLost(self):
        if taskMgr.hasTaskNamed(self.hbTaskName):
            taskMgr.remove(self.hbTaskName)
        
        self.agent.removeChannel(self.channel)
        
    def drop(self, code, reason):
        self.agent.closeConnection(code, reason, self.connection)
        
    def handleMessage(self, dg):
        connection = dg.getConnection()
        di = PyDatagramIterator(dg)
        msgType = di.getUint16()
        
        if msgType == CLIENT_HEARTBEAT:
            self.heartbeat()
        elif msgType == CLIENT_LOGIN_2:
            self.__handleLogin(dg)
        else:
            self.agent.handleDatagram(dg)
            
    def __handleLogin(self, dg):
        playToken = dg.getString()
        clientVersion = dg.getString()
        hashVal = dg.getUint32()
        tokenType = dg.getInt32()
           
        if tokenType != CLIENT_LOGIN_2_BLUE:
            self.drop(CLIENT_DISCONNECT_INVALID_PLAY_TOKEN_TYPE, "Invalid playtoken type")
            return
            
        if hashVal != self.agent.hashVal:
            self.drop(CLIENT_DISCONNECT_BAD_DCHASH, "Invalid Hash")
            return
            
        if clientVersion != self.agent.serverVersion:
            self.drop(CLIENT_DISCONNECT_BAD_VERSION, "Invalid version")
            return
            
            
            
            
            
            
            
            
            