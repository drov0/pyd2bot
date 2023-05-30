from enum import Enum

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.bank.OpenBank import OpenBank
from pyd2bot.logic.roleplay.behaviors.movement.AutoTripUseZaap import \
    AutoTripUseZaap
from pyd2bot.misc.Localizer import Localizer
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.internalDatacenter.items.ItemWrapper import \
    ItemWrapper
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


class BankRetrieveStates(Enum):
    WAITING_FOR_MAP = -1
    IDLE = 0
    WALKING_TO_BANK = 1
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
        OpenBank().start(self.infos, callback=self.onStorageOpen, parent=self)
        
    def onStorageOpen(self, code, err):
        if err:
            return self.finish(code, err)
        KernelEventsManager().once(
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

    def onStorageClose(self, event, success):
        Logger().info("Bank storage closed")
        self.state = BankRetrieveStates.IDLE
        if self.return_to_start:
            Logger().info(f"Returning to start point")
            AutoTripUseZaap().start(self._startMapId, self._startRpZone, callback=self.finish, parent=self)
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
