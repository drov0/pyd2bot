from enum import Enum
from typing import TYPE_CHECKING

from pyd2bot.logic.common.frames.BotRPCFrame import BotRPCFrame
from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.AutoTrip import AutoTrip
from pyd2bot.logic.roleplay.behaviors.BotExchange import (
    BotExchange, ExchangeDirectionEnum)
from pyd2bot.misc.Localizer import Localizer
from pyd2bot.thriftServer.pyd2botService.ttypes import Character
from pydofus2.com.ankamagames.atouin.managers.MapDisplayManager import \
    MapDisplayManager
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionType import \
    ConnectionType
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

if TYPE_CHECKING:
    from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayEntitiesFrame import \
        RoleplayEntitiesFrame

class GiveItelsStates(Enum):
    WAITING_FOR_MAP = -1
    IDLE = 0
    WALKING_TO_BANK = 1
    ISIDE_BANK = 2
    RETURNING_TO_START_POINT = 4
    WAITING_FOR_SELLER = 5
    WAITING_FOR_SELLER_IDLE = 7
    IN_EXCHANGE_WITH_SELLER = 6

class GiveItems(AbstractBehavior):
    SELLER_BUSY = 8803
    
    def __init__(self):
        super().__init__()

    def run(self, sellerInfos: Character, return_to_start=True) -> bool:
        Logger().info("[GiveItems] started")
        self.seller = sellerInfos
        self.return_to_start = return_to_start
        self._startMapId = PlayedCharacterManager().currentMap.mapId
        self._startRpZone = PlayedCharacterManager().currentZoneRp
        self.bankInfos = Localizer.getBankInfos()
        self.state = GiveItelsStates.IDLE
        self.lastSellerState = "unknown"
        self._run()

    @property
    def entitiesFrame(self) -> "RoleplayEntitiesFrame":
        return Kernel().worker.getFrameByName("RoleplayEntitiesFrame")

    @property
    def rpcFrame(self) -> "BotRPCFrame":
        return Kernel().worker.getFrameByName("BotRPCFrame")

    def _run(self):
        if PlayedCharacterManager().currentMap is None:
            Logger().warning(f"[GiveItems] Player map not processed yet")
            return KernelEventsManager().onceMapProcessed(self._run, originator=self)
        Logger().debug(f"[GiveItems] Asked for seller status ...")
        self.checkGuestStatus()
        
    def getGuestStatus(self, instanceId):
        if not ConnectionsHandler.getInstance(instanceId) or \
            ConnectionsHandler.getInstance(instanceId).connectionType == ConnectionType.DISCONNECTED:
            return "disconnected"
        elif ConnectionsHandler.getInstance(instanceId).connectionType == ConnectionType.TO_LOGIN_SERVER:
            return "authenticating"
        elif not PlayedCharacterManager.getInstance(instanceId):
            return "loadingPlayer"
        elif PlayedCharacterManager.getInstance(instanceId).isInFight:
            return "fighting"
        elif not Kernel.getInstance(instanceId).entitiesFrame:
            return "outOfRolePlay"
        elif MapDisplayManager.getInstance(instanceId).currentDataMap is None:
            return "loadingMap"
        elif not Kernel.getInstance(instanceId).entitiesFrame.mcidm_processed:
            return "processingMapData"
        for behavior in AbstractBehavior.getSubs(instanceId):
            return str(behavior)
        return "idle"

    def checkGuestStatus(self):
        self.state = GiveItelsStates.WAITING_FOR_SELLER_IDLE
        self.lastSellerState = self.getGuestStatus(self.seller.login)
        while self.lastSellerState != "idle":
            Logger().info(f"[GiveItems] Seller status: {self.lastSellerState}.")
            if Kernel().worker.terminated.wait(2):
                return Logger().warning("Worker finished while fetching player status returning")
            self.lastSellerState = self.getGuestStatus(self.seller.login)
        self.state = GiveItelsStates.WALKING_TO_BANK
        AutoTrip().start(self.bankInfos.npcMapId, 1, callback=self.onTripEnded, parent=self)

    def onTripEnded(self, errorId, error):
        if error:
            return self.finish(errorId, error)
        if self.state == GiveItelsStates.RETURNING_TO_START_POINT:
            Logger().info("[UnloadInSellerFrame] Trip ended, returned to start point")
            return self.finish(True, None)
        elif self.state == GiveItelsStates.WALKING_TO_BANK:
            Logger().info("[UnloadInSellerFrame] Trip ended, waiting for seller to come")
            self.state = GiveItelsStates.WAITING_FOR_SELLER
            def onSellerResponse(result, error, sender):
                if not result:
                    return self.finish(self.SELLER_BUSY, f"Seller refused come to collect ask")
                self.waitForGuestToComme()
            self.rpcFrame.askComeToCollect(self.seller.login, self.bankInfos, BotConfig().character, onSellerResponse)

    def waitForGuestToComme(self):
        if self.entitiesFrame:
            if self.entitiesFrame.getEntityInfos(self.seller.id):
                BotExchange().start(ExchangeDirectionEnum.GIVE, target=self.seller, callback=self.onExchangeConcluded, parent=self)
                self.state = GiveItelsStates.IN_EXCHANGE_WITH_SELLER
                return True
            else:
                KernelEventsManager().onceActorShowed(self.seller.id, self.waitForGuestToComme, originator=self)
        else:
            KernelEventsManager().onceFramePushed("RoleplayEntitiesFrame", self.waitForGuestToComme, originator=self)

    def onExchangeConcluded(self, errorId, error) -> bool:
        if error:            
            if errorId == 5023: # guest doesnt have enough space
                Logger().error(error)
                Kernel().worker.terminated.wait(5)
                return self.checkGuestStatus(self.seller.login)
            return self.finish(errorId, error)
        if not self.return_to_start:
            return self.finish(True, None)
        else:
            self.state = GiveItelsStates.RETURNING_TO_START_POINT
            AutoTrip().start(self._startMapId, self._startRpZone, callback=self.onTripEnded, parent=self)
    
    def getState(self):
        state = self.state.name 
        if self.state == GiveItelsStates.WAITING_FOR_SELLER_IDLE:
            state += f":{self.lastSellerState}"
        elif AutoTrip().isRunning():
            state += f":{AutoTrip().getState()}"
        elif BotExchange().isRunning():
            state += f":{BotExchange().getState()}"
        return state