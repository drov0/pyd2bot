import threading
from time import perf_counter, sleep
from pyd2bot.apis.PlayerAPI import PlayerAPI
from pyd2bot.thriftServer.pyd2botService.ttypes import Session
from pydofus2.com.DofusClient import DofusClientThread
from pydofus2.com.ankamagames.dofus.kernel.net.DisconnectionReasonEnum import DisconnectionReasonEnum
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.metaclasses.Singleton import Singleton
from pyd2bot.logic.managers.PathManager import PathManager
    
logger = Logger()

class SessionTypeEnum:
    FIGHT = "fight"
    FARM = "farm"
    SELL = "selling"
class InactivityMonitor(threading.Thread):
    
    def __init__(self, name="InactivityMonitor", group=None):
        super().__init__(name=name)
        self.lastActivity = perf_counter()
        self.maxInactivityInterval = 60 * 60 * 2 if BotConfig().type == SessionTypeEnum.SELL else 60 * 15
        self.lastStatus = "disconnected"
        self.stop = threading.Event()
        self.group = group
    
    def run(self):
        while not self.stop.is_set():
            status = PlayerAPI.status()
            if status != self.lastStatus:
                self.lastActivity = perf_counter()
            elif perf_counter() - self.lastActivity > self.maxInactivityInterval:
                DofusClientThread().shutdown(DisconnectionReasonEnum.EXCEPTION_THROWN, "Fatal Error bot stayed inactive for too long")
                self.stop.set()
                return 1
            self.lastStatus = status
            sleep(1)
        logger.info("Inactivity monitor stopped")
            
class BotConfig(metaclass=Singleton):

    def __init__(self) -> None:
        self.character = None
        self.path = None
        self.isLeader: bool = None
        self.leader = None
        self.followers: list[str] = None
        self.jobIds = None
        self.resourceIds = None
        self.id = None
        self.type = None
        self.seller = None
        self.unloadType = None
        
    def initFromSession(session: Session, character):
        pass
    def loadFromJson(self, sessionJson: dict):
        self.id = sessionJson.get("id")
        self.type = sessionJson.get("type")
        self.character = sessionJson.get("character")
        self.unloadType = sessionJson.get("unloadType")
        self.seller = sessionJson.get("seller")
        if self.type == SessionTypeEnum.FARM:
            self.path = sessionJson.get("path")
            self.jobIds = sessionJson.get("jobIds")
            self.resourceIds = sessionJson.get("resourceIds")
        elif self.type == SessionTypeEnum.FIGHT:
            self.followers : list[str] = sessionJson.get("followers")
            self.monsterLvlCoefDiff = float(sessionJson.get("monsterLvlCoefDiff"))
            if self.followers is not None:
                self.party = True
                self.isLeader = True
                logger.info(f"Running path {self.path}")
            else:
                self.isLeader = False
                self.leader : int = sessionJson.get("leader")
        self.path = sessionJson.get("path")
        if self.path:
            self.path = PathManager.from_json(sessionJson["path"])

