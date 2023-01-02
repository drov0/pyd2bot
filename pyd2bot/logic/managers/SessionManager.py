import json
import threading
from time import perf_counter, sleep
from pyd2bot.apis.PlayerAPI import PlayerAPI
from pydofus2.com.DofusClient import DofusClient
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.metaclasses.Singleton import Singleton
from pyd2bot.logic.managers.PathManager import PathManager
from pydofus2.com.ankamagames.haapi.Haapi import Haapi

    
logger = Logger()

class SessionTypeEnum:
    FIGHT = "fight"
    FARM = "farm"
    SELL = "selling"
class InactivityMonitor(threading.Thread):
    
    def __init__(self):
        super().__init__()
        self.lastActivity = perf_counter()
        self.maxInactivityInterval = 60 * 60 * 2 if SessionManager().type == "selling" else 60 * 15
        self.lastStatus = "disconnected"
        self.stop = threading.Event()
    
    def run(self):
        while not self.stop.is_set():
            status = PlayerAPI.status()
            if status != self.lastStatus:
                self.lastActivity = perf_counter()
            elif perf_counter() - self.lastActivity > self.maxInactivityInterval:
                logger.info("Inactivity detected, disconnecting ...")
                DofusClient().restart()
                self.lastActivity = perf_counter()
            self.lastStatus = status
            sleep(1)
            
class SessionManager(metaclass=Singleton):
    character = None
    path = None
    isLeader: bool = None
    leader = None
    followers: list[str] = None
    jobIds = None
    resourceIds = None
    id = None

    def __init__(self) -> None:
        pass
    
    def generateLoginToken(self, login, password, certId, certHash):
        self.loginToken = Haapi().getLoginToken(login, password, certId, certHash)
        
    def load(self, sessionstr: str):
        sessionJson = json.loads(sessionstr)
        self.key = sessionJson.get("key")
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
            self.party = True
            if self.followers is not None:
                self.monsterLvlCoefDiff = float(sessionJson.get("monsterLvlCoefDiff"))
                self.isLeader = True
                self.path = sessionJson.get("path")
                logger.info(f"Running path {self.path}")
            else:
                self.isLeader = False
                self.leader : int = sessionJson.get("leader")
        if self.path:
            self.path = PathManager.from_json(sessionJson["path"])

