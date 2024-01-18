import random
import time

from pyd2bot.logic.common.frames.BotCharacterUpdatesFrame import \
    BotCharacterUpdatesFrame
from pyd2bot.logic.common.frames.BotRPCFrame import BotRPCFrame
from pyd2bot.logic.common.frames.BotWorkflowFrame import BotWorkflowFrame
from pyd2bot.logic.common.rpcMessages.PlayerConnectedMessage import \
    PlayerConnectedMessage
from pyd2bot.logic.fight.frames.BotFightFrame import BotFightFrame
from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.farm.ResourceFarm import ResourceFarm
from pyd2bot.logic.roleplay.behaviors.fight.FarmFights import FarmFights
from pyd2bot.logic.roleplay.behaviors.fight.MuleFighter import MuleFighter
from pyd2bot.logic.roleplay.behaviors.fight.SoloFarmFights import \
    SoloFarmFights
from pyd2bot.logic.roleplay.behaviors.quest.ClassicTreasureHunt import \
    ClassicTreasureHunt
from pyd2bot.thriftServer.pyd2botService.ttypes import (Session,
                                                        SessionStatus, SessionType)
from pydofus2.com.ankamagames.atouin.managers.MapDisplayManager import \
    MapDisplayManager
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionType import \
    ConnectionType
from pydofus2.com.ankamagames.dofus.kernel.net.DisconnectionReasonEnum import \
    DisconnectionReasonEnum
from pydofus2.com.ankamagames.dofus.logic.common.managers.PlayerManager import \
    PlayerManager
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.DofusClient import DofusClient


class Pyd2Bot(DofusClient):

    def __init__(self, session: Session):
        super().__init__(session.character.login)
        self._apiKey = session.apikey
        self._session = session
        self._character = session.character
        self._serverId = session.character.serverId
        self._characterId = session.character.id
        self._certId = session.cert.id if session.cert else ''
        self._certHash = session.cert.hash if session.cert else ''
        self.earnedKamas = 0
        self._totalKamas = None
        self.earnedLevels = 0
        self.nbrFightsDone = 0
        self.startTime = None
        self.mule = (session.type == SessionType.MULE_FIGHT)
        self._shutDownListeners = []

    def onRestart(self, event, message):
        self.onReconnect(event, message)

    def onReconnect(self, event, message, afterTime=0):
        if BotConfig().hasSellerLock:
            BotConfig().releaseSellerLock()
        AbstractBehavior.clearAllChilds()
        return super().onReconnect(event, message, afterTime)
    
    def onInGame(self):
        Logger().info(f"Character {self.name} is now in game.")
        if self._session.type == SessionType.SELL:
            BotConfig.SELLER_VACANT.set()
        for instId, inst in Kernel.getInstances():
            if instId != self.name:
                inst.worker.process(PlayerConnectedMessage(self.name))
        KernelEventsManager().on(KernelEvent.KamasUpdate, self.onKamasUpdate)
        KernelEventsManager().on(KernelEvent.PlayerLeveledUp, self.onLvlUp)
        self.startSessionMainBehavior()

    def onKamasUpdate(self, event, totalKamas):
        Logger().debug(f"Player kamas : {totalKamas}")
        if self._totalKamas is not None:
            diff = totalKamas - self._totalKamas
            if diff > 0:
                self.earnedKamas += diff
        self._totalKamas = totalKamas
        
    def onFight(self, event):
        Kernel().worker.addFrame(BotFightFrame())
        self.nbrFightsDone += 1
    
    def onLvlUp(self, event, previousLevel, newLevel):
        self.earnedLevels += (newLevel - previousLevel)
    
    def onMainBehaviorFinish(self, code, err):
        if err:
            Logger().error(err, exc_info=True)
            self.shutdown(DisconnectionReasonEnum.EXCEPTION_THROWN, err)
        else:
            self.shutdown(DisconnectionReasonEnum.WANTED_SHUTDOWN, "main behavior ended successfully")
    
    def startSessionMainBehavior(self):
        Logger().info(f"Starting main behavior for {self.name}")
    
        if BotConfig().isFarmSession:
            Logger().info(f"Starting farm behavior for {self.name}")
            ResourceFarm().start()
            
        elif BotConfig().isFightSession:
            Logger().info(f"Starting fight behavior for {self.name}")
            if BotConfig().isLeader:
                if BotConfig().followers:
                    FarmFights().start(callback=self.onMainBehaviorFinish)
                else:
                    SoloFarmFights().start(callback=self.onMainBehaviorFinish)
            else:
                MuleFighter().start(callback=self.onMainBehaviorFinish)
                
        elif BotConfig().isTreasureHuntSession:
            Logger().info(f"Starting treasure hunt behavior for {self.name}")
            ClassicTreasureHunt().start(callback=self.onMainBehaviorFinish)
            
        elif BotConfig().isMixed:
            activity = random.choice([ResourceFarm(60 * 5), SoloFarmFights(60 * 3)])
            activity.start(callback=self.switchActivity)
        
    def switchActivity(self, code, err):
        self.onReconnect(None, f"Fake disconnect and take nap", random.random() * 60 * 3)

    def run(self):
        self.startTime = time.time()
        BotConfig().initFromSession(self._session)
        self.registerInitFrame(BotWorkflowFrame)
        self.registerInitFrame(BotRPCFrame)
        self.registerGameStartFrame(BotCharacterUpdatesFrame)
        return super().run()

    def getState(self):
        if self.terminated.is_set():
            if self._crashed:
                return SessionStatus.CRASHED
            else:
                return SessionStatus.TERMINATED
        if not ConnectionsHandler.getInstance(self.name) or \
            ConnectionsHandler.getInstance(self.name).connectionType == ConnectionType.DISCONNECTED:
            return SessionStatus.DISCONNECTED
        elif ConnectionsHandler.getInstance(self.name).connectionType == ConnectionType.TO_LOGIN_SERVER:
            return SessionStatus.AUTHENTICATING
        if PlayedCharacterManager.getInstance(self.name).isInFight:
            return SessionStatus.FIGHTING
        elif not Kernel.getInstance(self.name).roleplayEntitiesFrame:
            return SessionStatus.OUT_OF_ROLEPLAY
        elif MapDisplayManager.getInstance(self.name).currentDataMap is None:
            return SessionStatus.LOADING_MAP
        elif not Kernel.getInstance(self.name).roleplayEntitiesFrame.mcidm_processed:
            return SessionStatus.PROCESSING_MAP
        if AbstractBehavior.hasRunning(self.name):
            return SessionStatus.ROLEPLAYING
        return SessionStatus.IDLE
