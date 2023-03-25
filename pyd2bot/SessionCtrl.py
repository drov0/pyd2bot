import json
import os
import time

from pyd2bot.logic.managers.BotConfig import CharacterRoleEnum
from pyd2bot.Pyd2Bot import Pyd2Bot
from pyd2bot.thriftServer.pyd2botService.ttypes import (Character, DofusError,
                                                        Path, PathType,
                                                        RunSummary, Session,
                                                        SessionType,
                                                        UnloadType, Vertex)
from pydofus2.com.ankamagames.dofus.kernel.net.DisconnectionReasonEnum import \
    DisconnectionReasonEnum
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

__dir = os.path.dirname(os.path.abspath(__file__))
persistence_dir = os.path.join(__dir, "..", "..", "Grinder", "dist_electron", "persistence")
accounts_jsonfile = os.path.join(persistence_dir, "accounts.json")
creds_jsonfile = os.path.join(persistence_dir, "credentials.json")


class SessionCtrl:
    INVALID_SESSION_TYPE = 77896

    def __init__(self) -> None:
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

    def createFightSession(self, leaderId, followersIds, sellerId, path, monsterLvlCoefDiff) -> Session:
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

    def stopCharacter(self, login, reason="N/A", crash=False):
        bot = self._running.get(login)
        if not bot:
            return Logger().error(f"Character {login} is not running")
        bot.shutdown(DisconnectionReasonEnum.WANTED_SHUTDOWN, reason)

    def startCharacter(self, character: Character, role: CharacterRoleEnum, session: Session):
        if character.login in self._running:
            Logger().warning(f"Character {character.login} is already running")
            return
        login = character.login
        cert = self.creds["certificates"][login]
        key = self.creds["apikeys"][login]["key"]
        bot = Pyd2Bot(login)

        def onShutDown():
            Logger().warning(f"Character {login} shutdowned")
            if bot._crashed and session.type == SessionType.FIGHT:
                return self.stopFightSession(
                    session, f"Character {login} crached for reason : {bot._crashMessage}", True
                )
            self.stopCharacter(login, bot._shutDownReason)

        bot.addShutDownListener(onShutDown)
        bot.setConfig(key, cert["id"], cert["hash"], session, role, character)
        bot.start()
        self._running[login] = bot

    def addTeam(self, name, leaderId, followersIds, sellerId, mapId, monsterLvlCoefDiff=None):
        path = self.getPath(mapId)
        session = self.createFightSession(leaderId, followersIds, sellerId, path, monsterLvlCoefDiff)
        self._sessions[name] = session

    def addSession(self, session: Session):
        self._sessions[session.id] = session
        return True

    def startSession(self, session: Session):
        if session.id not in self._sessions:
            self._sessions[session.id] = session
        if session.type == SessionType.FIGHT:
            self.startFightSession(session)
        elif session.type == SessionType.FARM:
            self.startFarmSession(session)
        else:
            raise DofusError(self.INVALID_SESSION_TYPE, f"Invalid session type {session.type}")
        return True

    def startFarmSession(self, session: Session):
        raise NotImplementedError()

    def startFightSession(self, session: Session):
        self.startCharacter(session.leader, CharacterRoleEnum.LEADER, session)
        if session.followers:
            for character in session.followers:
                self.startCharacter(character, CharacterRoleEnum.FOLLOWER, session)
        if session.unloadType == UnloadType.SELLER:
            self.startCharacter(session.seller, CharacterRoleEnum.SELLER, session)

    def startJoinAll(self):
        for name, session in self._sessions.items():
            Logger().info(f"Running session {name} ..")
            self.startSession(session)
            Logger().info(f"Session {name} started")
        for login, bot in self._running.items():
            bot.join()

    def getSession(self, sessionId) -> Session:
        return self._sessions.get(sessionId)

    def removeSession(self, sessionId):
        session = self._sessions[sessionId]
        del self._running[session.leader.id]
        if session.followers:
            for follower in session.followers:
                del self._running[follower.id]
        if session.seller:
            del self._running[session.seller.id]
        del self._sessions[sessionId]

    def stopFightSession(self, session: Session, reason="N/A", crash=False):
        self.stopCharacter(session.leader.login, reason, crash)
        if session.followers:
            for follower in session.followers:
                self.stopCharacter(follower.login, reason, crash)
        if session.unloadType == UnloadType.SELLER:
            self.stopCharacter(session.seller.login, reason, crash)
        if not crash:
            self.removeSession(session.id)

    def stopFarmSession(self, session: Session):
        raise DofusError(401, "Internal error : stop farm sessions not implemented yet")

    def stopSession(self, sessionId, reason="N/A", crash=False):
        session = self.getSession(sessionId)
        if not session:
            raise DofusError(403, f"No session with id {sessionId} found")
        if session.type == SessionType.FIGHT:
            self.stopFightSession(session, reason, crash)
        elif session.type == SessionType.FARM:
            self.stopFarmSession(session, reason, crash)
        return True

    def getRunningCharacter(self, login) -> Pyd2Bot:
        if login in self._running:
            return self._running[login]
        raise DofusError(404, f"Character {login} is not running")

    def getCharacterRunSummary(self, login) -> RunSummary:
        bot = self.getRunningCharacter(login)
        current_time = int(time.time())
        total_run_time = current_time - bot.startTime
        session_id = bot._session.id
        leader_login = bot._session.leader.login if bot._session.leader else None
        number_of_restarts = len(bot._reconnectRecord)
        status = bot.getState()
        status_reason = "N/A"
        if status == "crashed":
            status_reason = bot._crashMessage
        run_summary = RunSummary(
            login=login,
            startTime=bot.startTime,
            totalRunTime=total_run_time,
            sessionId=session_id,
            leaderLogin=leader_login,
            numberOfRestarts=number_of_restarts,
            status=status,
            statusReason=status_reason,
            earnedKamas=bot.earnedKamas,
            nbrFightsDone=bot.nbrFightsDone,
        )
        return run_summary

    def getRunSummary(self) -> list[RunSummary]:
        run_summaries = []
        for login, bot in self._running.items():
            run_summary = self.getCharacterRunSummary(login)
            run_summaries.append(run_summary)
        return run_summaries

    def getSessionRunSummary(self, sessionId) -> list[RunSummary]:
        session = self.getSession(sessionId)
        if not session:
            raise DofusError(404, "Session not found")
        run_summaries = list[RunSummary]()
        if session.type == SessionType.FIGHT:
            run_summary = self.getCharacterRunSummary(session.leader.login)
            run_summaries.append(run_summary)
            if session.followers:
                for follower in session.followers:
                    run_summary = self.getCharacterRunSummary(follower.login)
                    run_summaries.append(run_summary)
            if session.unloadType == UnloadType.SELLER and session.seller:
                run_summary = self.getCharacterRunSummary(session.seller.login)
                run_summaries.append(run_summary)
        else:
            raise DofusError(404, "Get farm session run summary not implemented yet")
        for summary in run_summaries:
            if summary.status == "crashed":
                self.removeSession(sessionId)
        return run_summaries
