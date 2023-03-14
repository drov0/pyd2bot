from enum import Enum
from typing import TYPE_CHECKING
from pyd2bot.logic.common.frames.BotRPCFrame import BotRPCFrame
from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.AutoTrip import AutoTrip
from pyd2bot.logic.roleplay.frames.BotExchangeFrame import (
    BotExchangeFrame, ExchangeDirectionEnum)
from pyd2bot.misc.BotEventsmanager import BotEventsManager
from pyd2bot.misc.Localizer import Localizer
from pyd2bot.thriftServer.pyd2botService.ttypes import Character
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
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
    IN_EXCHANGE_WITH_SELLER = 6

class GiveItems(AbstractBehavior):

    def __init__(self):
        super().__init__()

    def start(self, sellerInfos: Character, callback, return_to_start=True) -> bool:
        if self.running.is_set():
            return self.finish(False, "Already running")
        Logger().info("[GiveItems] started")
        self.running.set()
        self.seller = sellerInfos
        self.return_to_start = return_to_start
        self.callback = callback        
        self._startMapId = PlayedCharacterManager().currentMap.mapId
        self._startRpZone = PlayedCharacterManager().currentZoneRp
        self.bankInfos = Localizer.getBankInfos()
        self.state = GiveItelsStates.IDLE
        self._start()
        return True

    @property
    def entitiesFrame(self) -> "RoleplayEntitiesFrame":
        return Kernel().worker.getFrameByName("RoleplayEntitiesFrame")

    @property
    def rpcFrame(self) -> "BotRPCFrame":
        return Kernel().worker.getFrameByName("BotRPCFrame")

    def _start(self):
        if PlayedCharacterManager().currentMap is None:
            Logger().warning(f"[GiveItems] Player map not processed yet")
            return KernelEventsManager().onceMapProcessed(self._start, originator=self)
        Logger().debug(f"[GiveItems] Asked for seller status ...")
        self.rpcFrame.askForStatus(self.seller.login, self.onGuestStatus)

    def onGuestStatus(self, result: str, error: str, sender: str):
        if error:
            if error == self.rpcFrame.DEST_KERNEL_NOT_FOUND:
                Logger().warning("Seller is disconnected, waiting for him to connect ...")                    
                return BotEventsManager().onceBotConnected(
                    self.seller.login, 
                    lambda:self.rpcFrame.askForStatus(self.seller.login, self.onGuestStatus),
                    timeout=30,
                    ontimeout=lambda: self.finish(False, f"Wait for seller {self.seller.login} to connect timedout"), originator=self
                )
            return self.finish(False, f"Error while fetching guest {sender} status: {error}")
        Logger().info(f"[GiveItems] Seller status: {result}.")
        if result == "idle":
            self.rpcFrame.askComeToCollect(self.seller.login, self.bankInfos, BotConfig().character)
            self.state = GiveItelsStates.WALKING_TO_BANK
            AutoTrip().start(self.bankInfos.npcMapId, 1, self.onTripEnded)
        else:
            if Kernel().worker.terminated.wait(2):
                return Logger().warning("Worker finished while fetching player status returning")
            self.rpcFrame.askForStatus(self.seller.login, self.onGuestStatus)

    def onTripEnded(self, errorId, error):
        if error:
            return self.finish(errorId, error)
        if self.state == GiveItelsStates.RETURNING_TO_START_POINT:
            Logger().info("[UnloadInSellerFrame] Trip ended, returned to start point")
            return self.finish(True, None)
        elif self.state == GiveItelsStates.WALKING_TO_BANK:
            Logger().info("[UnloadInSellerFrame] Trip ended, waiting for seller to come")
            self.state = GiveItelsStates.WAITING_FOR_SELLER
            self.waitForGuestToComme()

    def waitForGuestToComme(self):
        if self.entitiesFrame:
            if self.entitiesFrame.getEntityInfos(self.seller.id):
                Kernel().worker.addFrame(BotExchangeFrame(ExchangeDirectionEnum.GIVE, target=self.seller, callback=self.onExchangeConcluded))
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
                return self.rpcFrame.askForStatus(self.seller.login, self.onGuestStatus)
            return self.finish(errorId, error)
        if not self.return_to_start:
            return self.finish(True, None)
        else:
            self.state = GiveItelsStates.RETURNING_TO_START_POINT
            AutoTrip().start(self._startMapId, self._startRpZone, self.onTripEnded)