from enum import Enum
import json
import threading
from time import sleep
from pyd2bot.logic.managers.SessionManager import SessionManager
from pyd2bot.logic.roleplay.frames.BotExchangeFrame import BotExchangeFrame, ExchangeDirectionEnum
from pyd2bot.logic.roleplay.messages.ExchangeConcludedMessage import ExchangeConcludedMessage
from pyd2bot.logic.roleplay.messages.SellerCollectedGuestItemsMessage import SellerCollectedGuestItemsMessage
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.MapComplementaryInformationsDataMessage import (
    MapComplementaryInformationsDataMessage,
)
from pydofus2.com.ankamagames.jerakine.messages.Frame import Frame
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.messages.Message import Message
from pydofus2.com.ankamagames.jerakine.types.enums.Priority import Priority
from pyd2bot.logic.roleplay.frames.BotAutoTripFrame import BotAutoTripFrame
from pyd2bot.logic.roleplay.messages.AutoTripEndedMessage import AutoTripEndedMessage
from pyd2bot.misc.Localizer import Localizer
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayEntitiesFrame import RoleplayEntitiesFrame

logger = Logger()

class UnloadInSellerStatesEnum(Enum):
    WAITING_FOR_MAP = -1
    IDLE = 0
    WALKING_TO_BANK = 1
    ISIDE_BANK = 2
    RETURNING_TO_START_POINT = 4
    WAITING_FOR_SELLER = 5
    IN_EXCHANGE_WITH_SELLER = 6


class BotUnloadInSellerFrame(Frame):
    PHENIX_MAPID = None

    def __init__(self, sellerInfos: dict, return_to_start=True):
        super().__init__()
        self.sellerInfos = sellerInfos
        self.return_to_start = return_to_start
        self.stopWaitingForSeller = threading.Event()

    def pushed(self) -> bool:
        logger.debug("BotUnloadInSellerFrame pushed")
        self.state = UnloadInSellerStatesEnum.IDLE
        self.stopWaitingForSeller.clear()
        if PlayedCharacterManager().currentMap is not None:
            self.start()
        else:
            self.state = UnloadInSellerStatesEnum.WAITING_FOR_MAP
        return True

    def pulled(self) -> bool:
        logger.debug("BotUnloadInSellerFrame pulled")
        transport, client = self.sellerInfos["client"]
        transport.close()
        self.stopWaitingForSeller.set()
        return True

    @property
    def priority(self) -> int:
        return Priority.VERY_LOW

    def connectToSellerServer(self):
        from pyd2bot.PyD2Bot import PyD2Bot

        transport, client = PyD2Bot().runClient('localhost', self.sellerInfos["serverPort"])
        self.sellerInfos["client"] = (transport, client)
        return transport, client
    
    @property
    def entitiesFrame(self) -> "RoleplayEntitiesFrame":
        return Kernel().getWorker().getFrame("RoleplayEntitiesFrame")
    
    def waitForSellerToComme(self):
        self.stopWaitingForSeller.clear()
        while not self.stopWaitingForSeller.is_set():
            if self.entitiesFrame:
                if self.entitiesFrame.getEntityInfos(self.sellerInfos["id"]):
                    logger.debug("Seller found in the bank map")
                    Kernel().getWorker().addFrame(BotExchangeFrame(ExchangeDirectionEnum.GIVE, target=self.sellerInfos))
                    self.state = UnloadInSellerStatesEnum.IN_EXCHANGE_WITH_SELLER
                    return True        
                else:
                    logger.debug("Seller not found in the bank map")
            else:
                logger.debug("No entitiesFrame found")
            sleep(2)
    
    def waitForSellerIdleStatus(self):
        transport, client = self.connectToSellerServer()
        currentMapId = PlayedCharacterManager().currentMap.mapId
        while not self.stopWaitingForSeller.is_set():
            sellerStatus = client.getStatus()
            logger.debug("Seller status: %s", sellerStatus)
            if sellerStatus == "idle":
                client.comeToBankToCollectResources(json.dumps(self.bankInfos.to_json()), json.dumps(SessionManager().character))
                if currentMapId != self.bankInfos.npcMapId:
                    Kernel().getWorker().addFrame(BotAutoTripFrame(self.bankInfos.npcMapId))
                    self.state = UnloadInSellerStatesEnum.WALKING_TO_BANK
                else:
                    threading.Thread(target=self.waitForSellerToComme, name=threading.current_thread().name).start()
                    self.state = UnloadInSellerStatesEnum.WAITING_FOR_SELLER
                return True
            sleep(2)
    
    def start(self):
        self.bankInfos = Localizer.getBankInfos()
        logger.debug("Bank infos: %s", self.bankInfos.__dict__)
        currentMapId = PlayedCharacterManager().currentMap.mapId
        self._startMapId = currentMapId
        self._startRpZone = PlayedCharacterManager().currentZoneRp
        threading.Thread(target=self.waitForSellerIdleStatus, name=threading.current_thread().name).start()

    def process(self, msg: Message) -> bool:

        if isinstance(msg, AutoTripEndedMessage):
            logger.debug("AutoTripEndedMessage received")
            if self.state == UnloadInSellerStatesEnum.RETURNING_TO_START_POINT:
                Kernel().getWorker().removeFrame(self)
                Kernel().getWorker().processImmediately(SellerCollectedGuestItemsMessage())
            elif self.state == UnloadInSellerStatesEnum.WALKING_TO_BANK:
                threading.Thread(target=self.waitForSellerToComme, name=threading.current_thread().name).start()
                self.state = UnloadInSellerStatesEnum.WAITING_FOR_SELLER
            return True

        elif isinstance(msg, MapComplementaryInformationsDataMessage):
            if self.state == UnloadInSellerStatesEnum.WAITING_FOR_MAP:
                self.state = UnloadInSellerStatesEnum.IDLE
                self.start()

        elif isinstance(msg, ExchangeConcludedMessage):
            if not self.return_to_start:
                Kernel().getWorker().removeFrame(self)
                Kernel().getWorker().processImmediately(SellerCollectedGuestItemsMessage())
            else:
                self.state = UnloadInSellerStatesEnum.RETURNING_TO_START_POINT
                Kernel().getWorker().addFrame(BotAutoTripFrame(self._startMapId, self._startRpZone))
                
    
