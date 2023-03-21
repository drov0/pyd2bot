from enum import Enum

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.AutoTrip import AutoTrip
from pyd2bot.logic.roleplay.behaviors.NpcDialog import NpcDialog
from pyd2bot.misc.Localizer import Localizer
from pydofus2.com.ankamagames.berilia.managers.EventsHandler import Listener
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.network.messages.game.dialog.LeaveDialogRequestMessage import \
    LeaveDialogRequestMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeLeaveMessage import \
    ExchangeLeaveMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeObjectTransfertAllFromInvMessage import \
    ExchangeObjectTransfertAllFromInvMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeStartedWithPodsMessage import \
    ExchangeStartedWithPodsMessage
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


class BankUnloadStates(Enum):
    WAITING_FOR_MAP = -1
    IDLE = 0
    WALKING_TO_BANK = 1
    INSIDE_BANK = 2
    INTERACTING_WITH_BANK_MAN = 3
    BANK_OPENED = 7
    BANK_OPEN_REQUESTED = 4
    UNLOAD_REQUEST_SENT = 6
    LEAVE_BANK_REQUESTED = 5
    RETURNING_TO_START_POINT = 8

class UnloadInBank(AbstractBehavior):

    def __init__(self):
        super().__init__()
        self.return_to_start = None
        self.callback = None

    def run(self, return_to_start=True, bankInfos=None) -> bool:
        self.return_to_start = return_to_start
        if bankInfos is None:
            self.infos = Localizer.getBankInfos()
        else:
            self.infos = bankInfos
        Logger().debug("Bank infos: %s", self.infos.__dict__)
        self._startMapId = PlayedCharacterManager().currentMap.mapId
        self._startRpZone = PlayedCharacterManager().currentZoneRp
        self.state = BankUnloadStates.WALKING_TO_BANK
        NpcDialog().start(
            self.infos.npcMapId, 
            self.infos.npcId, 
            self.infos.npcActionId, 
            [self.infos.openBankReplyId], 
            self.onBankManDialogEnded
        )
    
    def onBankManDialogEnded(self, status, error):
        if error:
            return self.finish(status, error)
        Logger().info("[UnloadInBank] Ended bank man dialog waiting for storage to open...")
        KernelEventsManager().once(KernelEvent.EXCHANGE_OPEN, self.onStorageOpen, originator=self)
        
    def onStorageOpen(self, event, msg: ExchangeStartedWithPodsMessage):
        Logger().info("[UnloadInBank] Bank storage open")
        self.nbrFails = 0
        def ontimeout(listener: Listener):
            self.nbrFails += 1
            if self.nbrFails > 10:
                return self.finish(False, "[UnloadInBank] transfer items to bank storage timeout")
            listener.armTimer()
            self.putAllItemsInBank()
        self.inventoryWeightListener = KernelEventsManager().once(
            KernelEvent.INVENTORY_WEIGHT_UPDATE, 
            self.onInventoryWeightUpdate, 
            timeout=3,
            ontimeout=ontimeout,
            originator=self
        )
        self.putAllItemsInBank()
        Logger().info("[UnloadInBank] Unload items in bank request sent")

    def onStorageClose(self, event, msg: ExchangeLeaveMessage):
        Logger().info("[UnloadInBank] Bank storage closed")
        self.state = BankUnloadStates.IDLE
        if self.return_to_start:
            Logger().info(f"[UnloadInBank] Returning to start point")
            AutoTrip().start(self._startMapId, self._startRpZone, callback=self.finish, parent=self)
        else:
            self.finish(True, None)

    def onInventoryWeightUpdate(self, event, weight, max):
        Logger().info(f"Inventory weight percent changed to : {round(100 * weight / max, 1)}%")
        self.nbrFails = 0
        def ontimeout(listener: Listener):
            self.nbrFails = 0
            if self.nbrFails > 10:
                return self.finish(False, "Bank close timedout!")
            listener.armTimer()
            self.leaveBank()
        self.storageCloseListener = KernelEventsManager().once(
            KernelEvent.EXCHANGE_CLOSE, 
            self.onStorageClose,
            timeout=10,
            ontimeout=ontimeout,
            originator=self
        )
        self.leaveBank()

    def leaveBank(self):
        rmsg = LeaveDialogRequestMessage()
        rmsg.init()
        self.state = BankUnloadStates.LEAVE_BANK_REQUESTED
        ConnectionsHandler().send(rmsg)

    def putAllItemsInBank(self):
        rmsg = ExchangeObjectTransfertAllFromInvMessage()
        rmsg.init()
        self.state = BankUnloadStates.UNLOAD_REQUEST_SENT
        ConnectionsHandler().send(rmsg)
