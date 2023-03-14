from typing import TYPE_CHECKING
from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import KernelEvent, KernelEventsManager
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import ConnectionsHandler
from pydofus2.com.ankamagames.dofus.kernel.net.DisconnectionReasonEnum import DisconnectionReasonEnum
from pydofus2.com.ankamagames.dofus.logic.connection.managers.AuthentificationManager import AuthentificationManager
from pydofus2.com.ankamagames.dofus.network.messages.game.approach.ReloginTokenRequestMessage import ReloginTokenRequestMessage
from pydofus2.com.ankamagames.jerakine.benchmark.BenchmarkTimer import BenchmarkTimer
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

if TYPE_CHECKING:
    pass

class ChangeServer(AbstractBehavior):

    def __init__(self) -> None:
        super().__init__()
        self.requestTimer = None

    def start(self, newServerId, callback=None) -> bool:
        if self.running.is_set():
            return self.finish(False, "[ChangeServer] Already running.")
        self.running.set()
        self.callback = callback
        self.newServerId = newServerId
        Logger().info("[ChangeServer] Started.")
        self.reloginTokenListener = KernelEventsManager().once(KernelEvent.RELOGIN_TOKEN, self.onReloginToken, originator=self)
        self.requestReloginToken()

    def onReloginToken(self, valid, token):
        if self.requestTimer:
            self.requestTimer.cancel()
        if not valid:
            return self.finish(False, "Received non valid token")
        self.reloginTokenListener = None
        AuthentificationManager()._lva.serverId = self.newServerId
        AuthentificationManager().setToken(token)
        ConnectionsHandler().closeConnection(DisconnectionReasonEnum.CHANGING_SERVER)
        self.finish(True, None, token=token)

    def finish(self, status, error, token=None):        
        if self.reloginTokenListener:
            KernelEventsManager().remove_listener(KernelEvent.RELOGIN_TOKEN, self.reloginTokenListener)
        super().finish(status, error, token=token)

    def requestReloginToken(self):
        def onTimeout():
            self.finish(False, "Request login token timedout")
        self.requestTimer = BenchmarkTimer(5, onTimeout)
        rtrccmsg = ReloginTokenRequestMessage()
        rtrccmsg.init()
        self.requestTimer.start()
        ConnectionsHandler().send(rtrccmsg)
