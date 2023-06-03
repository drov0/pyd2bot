import threading
from enum import Enum

from pyd2bot.logic.managers.PathFactory import PathFactory
from pyd2bot.thriftServer.pyd2botService.ttypes import (Character, Session,
                                                        SessionType,
                                                        UnloadType)
from pydofus2.com.ankamagames.jerakine.metaclasses.Singleton import Singleton


class CharacterRoleEnum(Enum):
    LEADER = 0
    FOLLOWER = 1
    SELLER = 2
    FARMER = 3


class BotConfig(metaclass=Singleton):
    SELLER_VACANT = threading.Event()
    SELLER_LOCK = threading.Lock()

    defaultBreedConfig = {
        10: {"primarySpellId": 13516, "primaryStat": 10},  # sadida  # ronce  #  force
        4: {"primarySpellId": 12902, "primaryStat": 10},  # sram  # Truanderie  # force
    }

    def __init__(self) -> None:
        self.character: Character = None
        self.path = None
        self.isLeader: bool = None
        self.isSeller = None
        self.isFollower = None
        self.leader: Character = None
        self.followers: list[Character] = None
        self.jobIds: list[int] = None
        self.resourceIds: list[int] = None
        self.id = None
        self.sessionType: SessionType = None
        self.seller: Character = None
        self.unloadType: UnloadType = None
        self.monsterLvlCoefDiff = float("inf")
        self.fightOptionsSent = False
        self.lastFightTime = 0
        self.fightOptions = []
        self.followersIds = []
        self.fightPartyMembers = list[Character]()
        self.hasSellerLock = False

    def releaseSellerLock(self):
        if self.hasSellerLock:
            if BotConfig.SELLER_LOCK.locked():
                BotConfig.SELLER_LOCK.release()
            BotConfig.SELLER_VACANT.set()
            

    def getPrimarySpellId(self, breedId: int) -> int:
        return self.defaultBreedConfig[breedId]["primarySpellId"]
    
    @property
    def primarySpellId(self) -> int:
        return self.defaultBreedConfig[self.character.breedId]["primarySpellId"]

    @property
    def primaryStatId(self) -> int:
        return self.defaultBreedConfig[self.character.breedId]["primaryStat"]

    @property
    def unloadInBank(self) -> bool:
        return self.isSeller or self.unloadType == UnloadType.BANK

    @property
    def unloadInSeller(self) -> bool:
        return not self.isSeller and self.unloadType == UnloadType.SELLER 

    @property
    def isFarmSession(self) -> bool:
        return self.sessionType == SessionType.FARM

    @property
    def isFightSession(self) -> bool:
        return self.sessionType == SessionType.FIGHT

    @property
    def isMixed(self) -> bool:
        return self.sessionType == SessionType.MIXED
    
    def getPlayerById(self, playerId: int) -> Character:
        if playerId == self.character.id:
            return self.character
        return self.getFollowerById(playerId)
    
    def getFollowerById(self, playerId) -> Character:
        for follower in self.followers:
            if follower.id == playerId:
                return follower

    def getFollowerByName(self, name) -> Character:
        for follower in self.followers:
            if follower.name == name:
                return follower

    def initFromSession(self, session: Session, role: CharacterRoleEnum, character: Character):
        self.id = session.id
        if not session.jobFilters:
            session.jobFilters = []
        self.jobFilter = { jf.jobId: jf.resoursesIds for jf in session.jobFilters }
        self.sessionType = session.type
        self.unloadType = session.unloadType
        self.followers = session.followers if session.followers else []
        self.followersIds = [follower.id for follower in self.followers]
        self.party = self.followers is not None and len(self.followers) > 0
        self.character = character
        self.isLeader = (role == CharacterRoleEnum.LEADER)
        self.isFollower = (role == CharacterRoleEnum.FOLLOWER)
        self.isSeller = (role == CharacterRoleEnum.SELLER)
        self.seller = session.seller
        if session.path:
            self.path = PathFactory.from_thriftObj(session.path)
        if self.monsterLvlCoefDiff:
            self.monsterLvlCoefDiff = (
                session.monsterLvlCoefDiff if session.monsterLvlCoefDiff is not None else float("inf")
            )
        self.leader = session.leader
        self.fightPartyMembers = self.followers + [self.character]
