from direct.showbase.ShowBase import ShowBase
from direct.directnotify import DirectNotifyGlobal
from otpr.md.MessageDirector import MessageDirector
from otpr.ca.ClientAgent import ClientAgent

class OTPRBase(ShowBase):
    notify = DirectNotifyGlobal.directNotify.newCategory("OTP")
    
    def __init__(self):
        ShowBase.__init__(self)
        self.__startServer()
        
    def __startServer(self):
        self.messageDirector = MessageDirector()
        self.messageDirector.startup()
        self.clientAgent = ClientAgent()
        self.clientAgent.startup()
        
        self.notify.info("Online")