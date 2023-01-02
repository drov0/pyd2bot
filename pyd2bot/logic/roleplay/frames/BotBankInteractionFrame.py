from threading import Timer
from pyd2bot.logic.roleplay.messages.BankInteractionEndedMessage import BankInteractionEndedMessage
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import ConnectionsHandler
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.npc.NpcDialogCreationMessage import (
    NpcDialogCreationMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.npc.NpcDialogQuestionMessage import NpcDialogQuestionMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.npc.NpcDialogReplyMessage import (
    NpcDialogReplyMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.npc.NpcGenericActionRequestMessage import (
    NpcGenericActionRequestMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.dialog.LeaveDialogRequestMessage import LeaveDialogRequestMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeLeaveMessage import ExchangeLeaveMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeObjectTransfertAllFromInvMessage import (
    ExchangeObjectTransfertAllFromInvMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeStartedWithStorageMessage import (
    ExchangeStartedWithStorageMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.items.InventoryWeightMessage import InventoryWeightMessage
from pydofus2.com.ankamagames.jerakine.messages.Frame import Frame
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.messages.Message import Message
from pydofus2.com.ankamagames.jerakine.types.enums.Priority import Priority
from pyd2bot.misc.Localizer import BankInfos

logger = Logger()

class BankUnloadStateEnum:
    UNLOAD_REQUEST_SENT = 0
    BANK_OPENED = 1
    IDLE = 2
    WAITING_FOR_BANKMAN_QUESTION = 3
    WAITING_FOR_BANKMAN_DIALOG = 3
    BANK_OPEN_REQUESTED = 4
    LEAVE_BANK_REQUESTED = 5

class BotBankInteractionFrame(Frame):
    PHENIX_MAPID = None

    def __init__(self, bankInfos : BankInfos):
        super().__init__()
        self.infos = bankInfos

    def pushed(self) -> bool:
        logger.debug("BotBankInteractionFrame pushed")
        self.state = BankUnloadStateEnum.IDLE
        self.talkToBankMan()
        return True

    def pulled(self) -> bool:
        logger.debug("BotBankInteractionFrame pulled")
        return True

    @property
    def priority(self) -> int:
        return Priority.VERY_LOW

    def start(self):
        logger.debug("Bank infos: %s", self.infos.__dict__)
        

    def process(self, msg: Message) -> bool:

        if isinstance(msg, NpcDialogCreationMessage):
            self.state = BankUnloadStateEnum.WAITING_FOR_BANKMAN_QUESTION
    
        elif isinstance(msg, NpcDialogQuestionMessage):
            if self.state == BankUnloadStateEnum.WAITING_FOR_BANKMAN_QUESTION:
                logger.debug("bank man dialog engaged")
                self.openBankExchange()
                self.requestTimer = Timer(3, self.openBankExchange)
                self.requestTimer.start()
                logger.debug("Bank reply to open bank storage sent")
                return True

            
        elif isinstance(msg, ExchangeStartedWithStorageMessage):
            if self.requestTimer:
                self.requestTimer.cancel()
            rmsg = ExchangeObjectTransfertAllFromInvMessage()
            rmsg.init()
            ConnectionsHandler.getConnection().send(rmsg)
            self.state = BankUnloadStateEnum.UNLOAD_REQUEST_SENT
            return True

        elif isinstance(msg, InventoryWeightMessage):
            if self.state == BankUnloadStateEnum.UNLOAD_REQUEST_SENT:
                rmsg = LeaveDialogRequestMessage()
                rmsg.init()
                ConnectionsHandler.getConnection().send(rmsg)
                self.state = BankUnloadStateEnum.LEAVE_BANK_REQUESTED
            return True

        elif isinstance(msg, ExchangeLeaveMessage):
            if self.state == BankUnloadStateEnum.LEAVE_BANK_REQUESTED:
                Kernel().getWorker().removeFrame(self)
                Kernel().getWorker().processImmediately(BankInteractionEndedMessage())
                return True

    def talkToBankMan(self):
        rmsg = NpcGenericActionRequestMessage()
        rmsg.init(self.infos.npcId, self.infos.npcActionId, self.infos.npcMapId)
        ConnectionsHandler.getConnection().send(rmsg)
        logger.debug("Open bank man dialog sent")
        self.state = BankUnloadStateEnum.WAITING_FOR_BANKMAN_DIALOG

    def openBankExchange(self):
        rmsg = NpcDialogReplyMessage()
        logger.debug(f"Open bank request sent")
        rmsg.init(self.infos.openBankReplyId)
        ConnectionsHandler.getConnection().send(rmsg)
        self.state = BankUnloadStateEnum.BANK_OPEN_REQUESTED