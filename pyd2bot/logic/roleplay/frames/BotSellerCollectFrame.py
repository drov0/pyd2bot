from pyd2bot.logic.roleplay.frames.BotBankInteractionFrame import BotBankInteractionFrame
from pyd2bot.logic.roleplay.frames.BotExchangeFrame import BotExchangeFrame, ExchangeDirectionEnum
from pyd2bot.logic.roleplay.messages.BankInteractionEndedMessage import BankInteractionEndedMessage
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
from pyd2bot.misc.Localizer import BankInfos
from enum import Enum
logger = Logger()
        
class SellerCollecteStateEnum(Enum):
    WATING_MAP = 0
    IDLE = 4
    GOING_TO_BANK = 1
    INSIDE_BANK = 8
    TREATING_BOT_UNLOAD = 2
    UNLOADING_IN_BANK = 3
    WAITING_FOR_BOT_TO_ARRIVE = 5
    EXCHANGING_WITH_GUEST = 6
    EXCHANGE_OPEN_REQUEST_RECEIVED = 7
    EXCHANGE_OPEN = 9
    EXCHANGE_ACCEPT_SENT = 10
    

class BotSellerCollectFrame(Frame):
    PHENIX_MAPID = None
    
    def __init__(self, bankInfos: BankInfos, guest: dict, items: list = None):
        self.guest = guest
        self.bankInfos = bankInfos
        self.items = items
        super().__init__()

    def pushed(self) -> bool:
        logger.debug("BotSellerCollectFrame pushed")
        self.state = SellerCollecteStateEnum.WATING_MAP
        if PlayedCharacterManager().currentMap is not None:
            self.state = SellerCollecteStateEnum.GOING_TO_BANK
            self.goToBank()
        return True

    def pulled(self) -> bool:
        logger.debug("BotSellerCollectFrame pulled")
        return True

    @property
    def priority(self) -> int:
        return Priority.VERY_LOW

    def goToBank(self):
        currentMapId = PlayedCharacterManager().currentMap.mapId
        if currentMapId != self.bankInfos.npcMapId:
            Kernel().getWorker().addFrame(BotAutoTripFrame(self.bankInfos.npcMapId))
        else:
            self.state = SellerCollecteStateEnum.INSIDE_BANK
            Kernel().getWorker().addFrame(BotExchangeFrame(ExchangeDirectionEnum.RECEIVE, self.guest, self.items))
            self.state = SellerCollecteStateEnum.EXCHANGING_WITH_GUEST
            
    def process(self, msg: Message) -> bool:
    
        if isinstance(msg, AutoTripEndedMessage):
            logger.debug("AutoTripEndedMessage received")
            if self.state == SellerCollecteStateEnum.GOING_TO_BANK:
                self.state = SellerCollecteStateEnum.INSIDE_BANK
                Kernel().getWorker().addFrame(BotExchangeFrame(ExchangeDirectionEnum.RECEIVE, self.guest, self.items))
                self.state = SellerCollecteStateEnum.EXCHANGING_WITH_GUEST
            return True

        elif isinstance(msg, MapComplementaryInformationsDataMessage):
            if self.state == SellerCollecteStateEnum.WATING_MAP:
                logger.debug("MapComplementaryInformationsDataMessage received")
                self.state = SellerCollecteStateEnum.GOING_TO_BANK
                self.goToBank()
                
        elif isinstance(msg, ExchangeConcludedMessage):
            logger.debug("Exchange with guest ended successfully")
            self.state = SellerCollecteStateEnum.UNLOADING_IN_BANK
            Kernel().getWorker().addFrame(BotBankInteractionFrame(self.bankInfos))
        
        elif isinstance(msg, BankInteractionEndedMessage):
            logger.debug("BankInteractionEndedMessage received")
            Kernel().getWorker().processImmediately(SellerCollectedGuestItemsMessage())
            Kernel().getWorker().removeFrame(self)

 