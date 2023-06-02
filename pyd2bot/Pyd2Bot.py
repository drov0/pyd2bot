import time
from datetime import datetime

from pyd2bot.logic.common.frames.BotCharacterUpdatesFrame import \
    BotCharacterUpdatesFrame
from pyd2bot.logic.common.frames.BotRPCFrame import BotRPCFrame
from pyd2bot.logic.common.frames.BotWorkflowFrame import BotWorkflowFrame
from pyd2bot.logic.common.rpcMessages.PlayerConnectedMessage import \
    PlayerConnectedMessage
from pyd2bot.logic.fight.frames.BotFightFrame import BotFightFrame
from pyd2bot.logic.managers.BotConfig import BotConfig, CharacterRoleEnum
from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.bank.RetrieveRecipeFromBank import \
    RetrieveRecipeFromBank
from pyd2bot.logic.roleplay.behaviors.farm.ResourceFarm import ResourceFarm
from pyd2bot.logic.roleplay.behaviors.fight.FarmFights import FarmFights
from pyd2bot.logic.roleplay.behaviors.fight.MuleFighter import MuleFighter
from pyd2bot.logic.roleplay.behaviors.fight.SoloFarmFights import \
    SoloFarmFights
from pyd2bot.thriftServer.pyd2botService.ttypes import (Character, Session,
                                                        SessionStatus)
from pydofus2.com.ankamagames.atouin.managers.MapDisplayManager import \
    MapDisplayManager
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.dofus.datacenter.jobs.Recipe import Recipe
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionType import \
    ConnectionType
from pydofus2.com.ankamagames.dofus.kernel.net.PlayerDisconnectedMessage import \
    PlayerDisconnectedMessage
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.jerakine.benchmark.BenchmarkTimer import \
    BenchmarkTimer
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.DofusClient import DofusClient


class Pyd2Bot(DofusClient):

    def __init__(self, name="unknown"):
        super().__init__(name)

    def setConfig(
        self,
        apiKey: str,
        certId: int,
        certHash: str,
        session: Session,
        role: CharacterRoleEnum,
        character: Character,
        mitmMode=False
    ):
        self._apiKey = apiKey
        self._certId = certId
        self._certHash = certHash
        self._session = session
        self._role = role
        self._character = character
        self._serverId = character.serverId
        self._characterId = character.id
        self.earnedKamas = 0
        self._totalKamas = None
        self.nbrFightsDone = 0
        self.startTime = None
        self.mule = role != CharacterRoleEnum.LEADER
        self.mitm = mitmMode

    def onRestart(self, event, message):
        self.onReconnect(event, message)

    def onReconnect(self, event, mesg):
        if BotConfig().hasSellerLock:
            BotConfig().releaseSellerLock()
        AbstractBehavior.clearAllChilds()
        return super().onReconnect(event, mesg)
    
    def onInGame(self, event, msg):
        if self._role == CharacterRoleEnum.SELLER:
            BotConfig.SELLER_VACANT.set()
        for instId, inst in Kernel.getInstances():
            if instId != self.name:
                inst.worker.process(PlayerConnectedMessage(self.name))
        KernelEventsManager().on(KernelEvent.FIGHT_STARTED, self.onFight)
        KernelEventsManager().on(KernelEvent.KamasUpdate, self.onKamasUpdate)
        if not Kernel().mitm:
            self.startSessionMainBehavior()

    def onKamasUpdate(self, event, totalKamas):
        if self._totalKamas is not None:
            diff = totalKamas - self._totalKamas
            if diff > 0:
                self.earnedKamas += diff
        self._totalKamas = totalKamas
        
    def onFight(self, event):
        Kernel().worker.addFrame(BotFightFrame())
        self.nbrFightsDone += 1
        
    def startSessionMainBehavior(self):
        if BotConfig().isFarmSession:
            ResourceFarm().start()
        elif BotConfig().isFightSession:
            if BotConfig().isLeader:
                if BotConfig().followers:
                    FarmFights().start()
                else:
                    SoloFarmFights().start()
            else:
                MuleFighter().start()

    def addShutDownListener(self, callback):
        self._shutDownListeners.append(callback)

    def onShutdown(self, event, message):
        super().onShutdown(event, message)
        for callback in self._shutDownListeners:
            callback()
        
    def run(self):
        self.startTime = time.time()
        BotConfig().initFromSession(self._session, self._role, self._character)
        self.registerInitFrame(BotWorkflowFrame)
        self.registerInitFrame(BotRPCFrame)
        self.registerGameStartFrame(BotCharacterUpdatesFrame)
        return super().run()

    def getState(self):
        if self.terminated.is_set():
            return SessionStatus.TERMINATED
        if self._crashed:
            return SessionStatus.CRASHED
        if not ConnectionsHandler.getInstance(self.name) or \
            ConnectionsHandler.getInstance(self.name).connectionType == ConnectionType.DISCONNECTED:
            return SessionStatus.DISCONNECTED
        elif ConnectionsHandler.getInstance(self.name).connectionType == ConnectionType.TO_LOGIN_SERVER:
            return SessionStatus.AUTHENTICATING
        if PlayedCharacterManager.getInstance(self.name).isInFight:
            return SessionStatus.FIGHTING
        elif not Kernel.getInstance(self.name).entitiesFrame:
            return SessionStatus.OUT_OF_ROLEPLAY
        elif MapDisplayManager.getInstance(self.name).currentDataMap is None:
            return SessionStatus.LOADING_MAP
        elif not Kernel.getInstance(self.name).entitiesFrame.mcidm_processed:
            return SessionStatus.PROCESSING_MAP
        if AbstractBehavior.hasRunning():
            return SessionStatus.ROLEPLAYING
        return SessionStatus.IDLE
