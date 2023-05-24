from enum import Enum

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.AutoTrip import AutoTrip
from pyd2bot.logic.roleplay.behaviors.NpcDialog import NpcDialog
from pyd2bot.misc.Localizer import Localizer
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.internalDatacenter.items.ItemWrapper import \
    ItemWrapper
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.network.enums.ExchangeTypeEnum import \
    ExchangeTypeEnum
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


class BankRetrieveStates(Enum):
    WAITING_FOR_MAP = -1
    IDLE = 0
    WALKING_TO_BANK = 1
    INSIDE_BANK = 2
    INTERACTING_WITH_BANK_MAN = 3
    BANK_OPENED = 7
    BANK_OPEN_REQUESTED = 4
    RETRIEVE_REQUEST_SENT = 6
    LEAVE_BANK_REQUESTED = 5
    RETURNING_TO_START_POINT = 8

class RetrieveItemsFromBank(AbstractBehavior):
    BANK_CLOSE_TIMEDOUT = 89987
    RETRIEVE_ITEMS_TIMEDOUT = 998877
    STORAGE_OPEN_TIMEDOUT = 9874521
    
    def __init__(self):
        super().__init__()
        self.return_to_start = None

    def run(self, items:list[ItemWrapper], quantities:list[int], return_to_start=True, bankInfos=None) -> bool:
        self.items = items
        self.quantities = quantities
        self.return_to_start = return_to_start
        if bankInfos is None:
            self.infos = Localizer.getBankInfos()
        else:
            self.infos = bankInfos
        Logger().debug("Bank infos: %s", self.infos.__dict__)
        self._startMapId = PlayedCharacterManager().currentMap.mapId
        self._startRpZone = PlayedCharacterManager().currentZoneRp
        self.state = BankRetrieveStates.WALKING_TO_BANK
        NpcDialog().start(
            self.infos.npcMapId, 
            self.infos.npcId, 
            self.infos.npcActionId, 
            [self.infos.openBankReplyId], 
            callback=self.onBankManDialogEnded,
            parent=self
        )

    def onBankManDialogEnded(self, code, error):
        if error:
            return self.finish(code, error)
        Logger().info("Ended bank man dialog waiting for storage to open...")
        KernelEventsManager().once(
            event_id=KernelEvent.ExchangeBankStartedWithStorage, 
            callback=self.onStorageOpen,
            timeout=30,
            ontimeout=lambda: self.finish(self.STORAGE_OPEN_TIMEDOUT, "Dialog with Bank NPC ended correctly but storage didnt open on time!"),
            originator=self
        )
        
    def onStorageOpen(self, event, exchangeType, pods):
        if exchangeType == ExchangeTypeEnum.BANK:
            self.inventoryWeightListener = KernelEventsManager().once(
                KernelEvent.INVENTORY_WEIGHT_UPDATE, 
                self.onInventoryWeightUpdate, 
                timeout=15,
                retryNbr=5,
                retryAction=self.pullItems,
                ontimeout=lambda: self.finish(self.RETRIEVE_ITEMS_TIMEDOUT, "Pull items from bank storage timeout"),
                originator=self
            )
            self.pullItems()
            Logger().info("Pull items request sent")
        else:
            raise Exception(f"Expected BANK storage to open but another type of exchange '{ExchangeTypeEnum.BANK}' opened!")

    def onStorageClose(self, event, success):
        Logger().info("Bank storage closed")
        self.state = BankRetrieveStates.IDLE
        if self.return_to_start:
            Logger().info(f"Returning to start point")
            AutoTrip().start(self._startMapId, self._startRpZone, callback=self.finish, parent=self)
        else:
            self.finish(True, None)

    def onInventoryWeightUpdate(self, event, weight, max):
        Logger().info(f"Inventory weight percent changed to : {round(100 * weight / max, 1)}%")
        self.storageCloseListener = KernelEventsManager().once(
            event_id=KernelEvent.EXCHANGE_CLOSE, 
            callback=self.onStorageClose,
            timeout=10,
            ontimeout=lambda: self.finish(self.BANK_CLOSE_TIMEDOUT, "Bank close timedout!"),
            retryNbr=5,
            retryAction=Kernel().commonExchangeManagementFrame.leaveShopStock,
            originator=self
        )
        Kernel().commonExchangeManagementFrame.leaveShopStock()

    def pullItems(self):
        ids = [it.objectUID for it in self.items]
        Kernel().exchangeManagementFrame.exchangeObjectTransfertListWithQuantityToInv(ids, self.quantities)
        self.state = BankRetrieveStates.RETRIEVE_REQUEST_SENT
