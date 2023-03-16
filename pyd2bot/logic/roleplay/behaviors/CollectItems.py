from enum import Enum
from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.AutoTrip import AutoTrip
from pyd2bot.logic.roleplay.behaviors.UnloadInBank import UnloadInBank    
from pyd2bot.logic.roleplay.frames.BotExchangeFrame import (
    BotExchangeFrame, ExchangeDirectionEnum)
from pyd2bot.misc.BotEventsmanager import BotEventsManager
from pyd2bot.misc.Localizer import BankInfos
from pyd2bot.thriftServer.pyd2botService.ttypes import Character
from pydofus2.com.ankamagames.berilia.managers.EventsHandler import Listener
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

class CollecteState(Enum):
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


class CollectItems(AbstractBehavior):

    def __init__(self):
        self.guestDisconnectedListener: Listener = None
        super().__init__()

    def start(self, bankInfos: BankInfos, guest: Character, items: list = None, callback=None) -> bool:
        if self.running.is_set():
            return self.finish(AbstractBehavior.ALREADY_RUNNING, f"Can't start collect with {guest.login} because Already running with guest {self.guest.login}")
        self.running.set()
        Logger().info(f"[CollectFromGuest] collect from {guest.login} started")
        self.guest = guest
        self.bankInfos = bankInfos
        self.items = items
        self.callback = callback
        self.state = CollecteState.GOING_TO_BANK
        self.guestDisconnectedListener = BotEventsManager().onceBotDisconnected(self.guest.login, self.onGuestDisconnected, originator=self)
        AutoTrip().start(self.bankInfos.npcMapId, 1, self.onTripEnded)

    def onGuestDisconnected(self):
        Logger().error("[CollectFromGuest] Guest disconnected!")
        if self.state == CollecteState.EXCHANGING_WITH_GUEST:
            Kernel().worker.removeFrameByName("BotExchangeFrame")
        self.finish(True, None)

    def onTripEnded(self, code, error):
        if not self.isRunning():
            return
        if error is not None:
            return self.finish(False, error)        
        self.state = CollecteState.EXCHANGING_WITH_GUEST
        Kernel().worker.addFrame(BotExchangeFrame(ExchangeDirectionEnum.RECEIVE, self.guest, self.onExchangeConcluded, self.items))
    
    def onExchangeConcluded(self, code, error):
        self.guestDisconnectedListener.delete()
        if error:
            if code == 516493: # Inventory full
                Logger().error(error)
                UnloadInBank().start(self.finish, True, self.bankInfos)
                self.state = CollecteState.UNLOADING_IN_BANK
                return
            return self.finish(code, error)
        Logger().info("[CollectFromGuest] Exchange with guest ended successfully.")
        UnloadInBank().start(self.finish, True, self.bankInfos)
        self.state = CollecteState.UNLOADING_IN_BANK

