import json
import os
from pyd2bot.Pyd2Bot import Pyd2Bot
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pyd2bot.logic.managers.BotConfig import CharacterRoleEnum
from pyd2bot.thriftServer.pyd2botService.ttypes import (
    Character,
    Path,
    PathType,
    Session,
    SessionType,
    UnloadType,
    Vertex,
)

class SessionManager:
    
    def __init__(self) -> None:
        __dir = os.path.dirname(os.path.abspath(__file__))
        persistence_dir = os.path.join(
            __dir, "..", "..", "Grinder", "dist_electron", "persistence"
        )
        accounts_jsonfile = os.path.join(persistence_dir, "accounts.json")
        creds_jsonfile = os.path.join(persistence_dir, "credentials.json")
        with open(accounts_jsonfile, "r") as fp:
            self.accounts: dict = json.load(fp)
        with open(creds_jsonfile, "r") as fp:
            self.creds: dict = json.load(fp)
        self._running = dict[str, Pyd2Bot]()
        self._sessions = dict[str, Session]()

    def getCharacterById(self, id) -> Character:
        for accId in self.accounts:
            if "characters" in self.accounts[accId]:
                for character in self.accounts[accId]["characters"]:
                    if character["id"] == id:
                        return Character(
                            name=character["name"],
                            id=character["id"],
                            level=character["level"],
                            breedId=character["breedId"],
                            breedName=character["breedName"],
                            serverId=character["serverId"],
                            serverName=character["serverName"],
                            login=self.accounts[accId]["login"],
                            accountId=accId,
                        )
        raise Exception(f"character id {id} not found")

    def getSession(
        self, leaderId, followersIds, sellerId, path, monsterLvlCoefDiff
    ) -> Session:
        return Session(
            id="test",
            leader=self.getCharacterById(leaderId),
            unloadType=UnloadType.SELLER,
            followers=[self.getCharacterById(id) for id in followersIds],
            type=SessionType.FIGHT,
            path=path,
            seller=self.getCharacterById(sellerId),
            monsterLvlCoefDiff=monsterLvlCoefDiff,
        )

    def getPath(self, mapId) -> Path:
        return Path(
            id="test_path",
            type=PathType.RandomSubAreaFarmPath,
            startVertex=Vertex(mapId=mapId, zoneId=1),
        )

    def startCharacter(
        self, character: Character, role: CharacterRoleEnum, session: Session
    ):
        if character.login in self._running:
            Logger().warning(f"Character {character.login} is already running")
            return
        login = character.login
        cert = self.creds["certificates"][login]
        key = self.creds["apikeys"][login]["key"]
        bot = Pyd2Bot(login)
        bot.setConfig(key, cert["id"], cert["hash"], session, role, character)
        bot.start()
        self._running[login] = bot

    def addTeam(
        self, name, leaderId, followersIds, sellerId, mapId, monsterLvlCoefDiff=None
    ):
        path = self.getPath(mapId)
        session = self.getSession(
            leaderId, followersIds, sellerId, path, monsterLvlCoefDiff
        )
        self._sessions[name] = session

    def startSession(self, session: Session):
        self.startCharacter(session.leader, CharacterRoleEnum.LEADER, session)
        for character in session.followers:
            self.startCharacter(character, CharacterRoleEnum.FOLLOWER, session)
        self.startCharacter(session.seller, CharacterRoleEnum.SELLER, session)

    def startJoinAll(self):
        for name, session in self._sessions.items():
            Logger().info(f"Running session {name} ..")
            self.startSession(session)
            Logger().info(f"Session {name} started")
        for login, bot in self._running.items():
            bot.join()