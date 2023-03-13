from enum import Enum
from pyd2bot.logic.roleplay.behaviors.UnloadInBank import UnloadInBank
from pyd2bot.thriftServer.pyd2botService.ttypes import Character
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import KernelEvent, KernelEventsManager
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import ConnectionsHandler
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.InventoryManager import InventoryManager
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.network.messages.game.dialog.LeaveDialogRequestMessage import LeaveDialogRequestMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeAcceptMessage import (
    ExchangeAcceptMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeIsReadyMessage import (
    ExchangeIsReadyMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeLeaveMessage import (
    ExchangeLeaveMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeObjectAddedMessage import (
    ExchangeObjectAddedMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeObjectMoveKamaMessage import (
    ExchangeObjectMoveKamaMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeObjectMoveMessage import (
    ExchangeObjectMoveMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeObjectsAddedMessage import (
    ExchangeObjectsAddedMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeObjectTransfertAllFromInvMessage import (
    ExchangeObjectTransfertAllFromInvMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangePlayerRequestMessage import (
    ExchangePlayerRequestMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeReadyMessage import (
    ExchangeReadyMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeRequestedTradeMessage import (
    ExchangeRequestedTradeMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeStartedWithPodsMessage import (
    ExchangeStartedWithPodsMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.items.ExchangeKamaModifiedMessage import (
    ExchangeKamaModifiedMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.items.ObjectDeleteMessage import ObjectDeleteMessage
from pydofus2.com.ankamagames.jerakine.benchmark.BenchmarkTimer import BenchmarkTimer
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.messages.Frame import Frame
from pydofus2.com.ankamagames.jerakine.messages.Message import Message
from pydofus2.com.ankamagames.jerakine.types.enums.Priority import Priority

class ExchangeDirectionEnum(Enum):
    GIVE = 0
    RECEIVE = 1

class ExchangeStateEnum(Enum):
    NOT_STARTED = -1
    IDLE = 0
    EXCHANGE_REQUEST_SENT = 1
    EXCHANGE_REQUEST_RECEIVED = 2
    EXCHANGE_REQUEST_ACCEPTED = 3
    EXCHANGE_OPEN = 4
    EXCHANGE_OBJECTS_ADDED = 5
    EXCHANGE_KAMAS_ADDED = 6
    EXCHANGE_READY_SENT = 7
    TERMINATED = 8

class BotExchangeFrame(Frame):
    PHENIX_MAPID = None

    def __init__(self, direction: str, target: Character, callback, items: list = None):
        self.direction = direction
        self.target = target
        self.items = items
        self.callback = callback
        self.state = ExchangeStateEnum.NOT_STARTED
        if items is None:
            self.giveAll = True
            self.step = 1
        else:
            self.giveAll = False
            self.step = len(items)
        self.wantsToMoveItemToExchange = set()
        self.acceptExchangeTimer: BenchmarkTimer = None
        self.openExchangeTimer: BenchmarkTimer = None
        self.exchangeLeaveListener = None
        self.nbrFails = 0
        super().__init__()

    def pushed(self) -> bool:
        self.state = ExchangeStateEnum.IDLE
        if self.direction == ExchangeDirectionEnum.GIVE:
            self.sendExchangeRequest()
        return True

    def pulled(self) -> bool:
        if self.acceptExchangeTimer is not None:
            self.acceptExchangeTimer.cancel()
        if self.openExchangeTimer is not None:
            self.openExchangeTimer.cancel()
        return True

    @property
    def priority(self) -> int:
        return Priority.VERY_LOW

    def onExchangeOpen(self, event, msg: ExchangeStartedWithPodsMessage):
        Logger().debug("[ExchangeFrame] Exchange started.")
        self.state = ExchangeStateEnum.EXCHANGE_OPEN
        if self.direction == ExchangeDirectionEnum.GIVE:
            if self.giveAll:
                ConnectionsHandler().send(ExchangeObjectTransfertAllFromInvMessage())
            else:
                for elem in self.items:
                    rmsg = ExchangeObjectMoveMessage()
                    rmsg.init(objectUID_=elem["uid"], quantity_=elem["quantity"])
                    ConnectionsHandler().send(rmsg)
                    self.wantsToMoveItemToExchange.add(elem["uid"])
            Logger().debug("[ExchangeFrame] Moved items to exchange.")

    def process(self, msg: Message) -> bool:

        if isinstance(msg, ExchangeRequestedTradeMessage):
            Logger().debug(f"[ExchangeFrame] Exchange request received from {msg.source} to {msg.target}")
            if msg.source == self.target.id:
                self.state = ExchangeStateEnum.EXCHANGE_REQUEST_RECEIVED
                ConnectionsHandler().send(ExchangeAcceptMessage())
                self.state = ExchangeStateEnum.EXCHANGE_REQUEST_ACCEPTED
            elif int(msg.source) == int(PlayedCharacterManager().id):
                if self.openExchangeTimer:
                    self.openExchangeTimer.cancel()
                self.state = ExchangeStateEnum.EXCHANGE_REQUEST_SENT
            return True

        elif isinstance(msg, ExchangeObjectsAddedMessage):
            Logger().debug("[ExchangeFrame] All items moved to exchange.")
            self.state = ExchangeStateEnum.EXCHANGE_OBJECTS_ADDED
            if self.direction == ExchangeDirectionEnum.GIVE:
                if self.giveAll:
                    BenchmarkTimer(3, self.sendAllKamas).start()
                else:
                    BenchmarkTimer(3, self.sendExchangeReady).start()
            return True

        elif isinstance(msg, ExchangeKamaModifiedMessage):
            Logger().debug(f"[ExchangeFrame] {msg.quantity} kamas added to exchange")
            self.state = ExchangeStateEnum.EXCHANGE_KAMAS_ADDED
            self.step += 1
            if self.direction == ExchangeDirectionEnum.GIVE:
                BenchmarkTimer(3, self.sendExchangeReady).start()
            return True

        elif isinstance(msg, ExchangeObjectAddedMessage):
            Logger().debug("[ExchangeFrame] Item added to exchange.")
            if self.direction == ExchangeDirectionEnum.GIVE:
                self.wantsToMoveItemToExchange.remove(msg.object.objectUID)
                if len(self.wantsToMoveItemToExchange) == 0:
                    Logger().debug("All items moved to exchange.")
                    self.state = ExchangeStateEnum.EXCHANGE_OBJECTS_ADDED
                    BenchmarkTimer(3, self.sendExchangeReady).start()
            return True

        elif isinstance(msg, ExchangeIsReadyMessage):
            Logger().debug(f"[ExchangeFrame] Exchange is ready received from target {int(msg.id)}.")
            if self.acceptExchangeTimer is not None:
                self.acceptExchangeTimer.cancel()
            if self.direction == ExchangeDirectionEnum.RECEIVE and int(msg.id) == int(self.target.id) and msg.ready:
                BenchmarkTimer(3, self.sendExchangeReady).start()
            return True

    def finish(self, status, error):
        Kernel().worker.removeFrame(self)
        self.callback(status, error)

    def sendExchangeRequest(self):
        msg = ExchangePlayerRequestMessage()
        msg.init(exchangeType_=1, target_=self.target.id)
        def onTimeout():
            self.nbrFails += 1
            if self.nbrFails > 3:
                return self.finish(False, "[ExchangeFrame] send exchange timedout")
            self.openExchangeTimer = BenchmarkTimer(5, onTimeout)
            self.openExchangeTimer.start()
            ConnectionsHandler().send(msg)
        self.openExchangeTimer = BenchmarkTimer(5, onTimeout)
        self.nbrFails = 0
        self.openExchangeTimer.start()
        KernelEventsManager().once(KernelEvent.EXCHANGE_OPEN, self.onExchangeOpen)
        ConnectionsHandler().send(msg)
        Logger().debug("[ExchangeFrame] Exchange open request sent")
        
    def onServerNotif(self, event, msgId, msgType, textId, text):
        KernelEventsManager().remove_listener(KernelEvent.TEXT_INFO, self.onServerNotif)
        KernelEventsManager().remove_listener(KernelEvent.EXCHANGE_CLOSE, self.exchangeLeaveListener)
        if textId == 516493: # inventory full
            if self.acceptExchangeTimer:
                self.acceptExchangeTimer.cancel()
            def onExchangeClose(event, msg):
                self.finish(516493, "[ExchangeFrame] Can't take guest items because we don't have enough space in inventory")
            KernelEventsManager().once(KernelEvent.EXCHANGE_CLOSE, onExchangeClose)
            ConnectionsHandler().send(LeaveDialogRequestMessage()) 
        elif textId == 5023: # the second player can't take all the load            
            timer = BenchmarkTimer(6, ConnectionsHandler().send, [LeaveDialogRequestMessage()])
            if self.acceptExchangeTimer:
                self.acceptExchangeTimer.cancel()
            def onExchangeClose(event, msg):
                if timer:
                    timer.cancel()
                self.finish(5023, "Can't give to guest items because he doesn't have enough space in inventory")
            KernelEventsManager().once(KernelEvent.EXCHANGE_CLOSE, onExchangeClose)
            timer.start()

    def onExchangeLeave(self, event, msg: ExchangeLeaveMessage):
        KernelEventsManager().remove_listener(KernelEvent.TEXT_INFO, self.onServerNotif)
        self.state = ExchangeStateEnum.TERMINATED
        if msg.success == True:
            if self.giveAll:
                if (PlayedCharacterManager().inventoryWeight / PlayedCharacterManager().inventoryWeightMax) > 0.9:
                    return self.finish(False, "Inventory still full when i am supposed to have given all items")
            Logger().info("[ExchangeFrame] Exchange ended successfully.")
            self.finish(True, None)
        else:
            self.finish(False, "Exchange failed")
            
    def sendExchangeReady(self):
        readymsg = ExchangeReadyMessage()
        readymsg.init(ready_=True, step_=self.step)
        self.acceptExchangeTimer = BenchmarkTimer(5, self.sendExchangeReady)
        self.acceptExchangeTimer.start()
        KernelEventsManager().on(KernelEvent.TEXT_INFO, self.onServerNotif)
        self.exchangeLeaveListener = KernelEventsManager().once(KernelEvent.EXCHANGE_CLOSE, self.onExchangeLeave)
        ConnectionsHandler().send(readymsg)
        Logger().debug("[ExchangeFrame] Exchange is ready sent.")

    def sendAllKamas(self):
        eomkm = ExchangeObjectMoveKamaMessage()
        kamas_quantity = InventoryManager().inventory.kamas
        Logger().debug(f"[ExchangeFrame] There is {kamas_quantity} in bots inventory.")
        eomkm.init(kamas_quantity)
        ConnectionsHandler().send(eomkm)
