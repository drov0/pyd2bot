from pyd2bot.thriftServer.pyd2botService.ttypes import Session, SessionType, Character, UnloadType
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.metaclasses.Singleton import Singleton
from pyd2bot.logic.managers.PathManager import PathManager
from enum import Enum
logger = Logger()

class CharacterRoleEnum(Enum):
    LEADER = 0
    FOLLOWER = 1
    SELLER = 2
class BotConfig(metaclass=Singleton):

    def __init__(self) -> None:
        self.character: Character = None
        self.path = None
        self.isLeader: bool = None
        self.leader: Character = None
        self.followers: list[Character] = None
        self.jobIds: list[int] = None
        self.resourceIds: list[int] = None
        self.id = None
        self.sessionType: SessionType = None
        self.seller: Character = None
        self.unloadType: UnloadType = None
        
    def initFromSession(self, session: Session, role: CharacterRoleEnum):
        self.id = session.id
        self.sessionType = session.type
        if session.type == SessionType.FARM:
            if role == CharacterRoleEnum.LEADER:
                self.leader = True
                self.character = session.leader
                self.unloadType = session.unloadType
                self.followers = session.followers
                self.path = PathManager.from_thriftObj(session.path)
                self.monsterLvlCoefDiff = session.monsterLvlCoefDiff
                if len(self.followers) > 0:
                    self.party = True
            elif role == CharacterRoleEnum.FOLLOWER:
                self.character = session.followers[0]
                self.leader = session.leader
                self.path = PathManager.from_thriftObj(session.path)
                self.monsterLvlCoefDiff = session.monsterLvlCoefDiff
                self.party = True
        else:
            raise Exception(f"Unsupported session type: {session.type}")
        
    def loadFromJson(self, sessionJson: dict):
        self.id = sessionJson.get("id")
        self.sessionType = sessionJson.get("type")
        self.character = sessionJson.get("character")
        self.unloadType = sessionJson.get("unloadType")
        self.seller = sessionJson.get("seller")
        if self.sessionType == SessionType.FARM:
            self.path = sessionJson.get("path")
            self.jobIds = sessionJson.get("jobIds")
            self.resourceIds = sessionJson.get("resourceIds")
        elif self.sessionType == SessionType.FIGHT:
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

