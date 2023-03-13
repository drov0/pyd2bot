from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pydofus2.com.ankamagames.atouin.managers.MapDisplayManager import MapDisplayManager
from pydofus2.com.ankamagames.berilia.managers.EventsHandler import Listener
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import KernelEventsManager
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import ConnectionsHandler
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.MapInformationsRequestMessage import MapInformationsRequestMessage
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

class RequestMapData(AbstractBehavior):
    REQUEST_MAPDATA_TIMEOUT = 3

    def __init__(self) -> None:
        self.mapDataRequestNbrFail = 0
        super().__init__()

    def start(self, callback) -> bool:
        if self.running.is_set():
            return self.finish(False, "Already running.")
        self.running.set()
        self.callback = callback
        Logger().info("Requesting data for map ")
        KernelEventsManager().onceMapProcessed(
            lambda: self.finish(True, None), 
            mapId=MapDisplayManager().currentMapPoint.mapId,
            timeout=self.REQUEST_MAPDATA_TIMEOUT,
            ontimeout=self.onMapDataRequestTimeout
        )
        self.sendRequest()

    def onMapDataRequestTimeout(self, listener: Listener):
        self.mapDataRequestNbrFail += 1
        if self.mapDataRequestNbrFail > 6:
            listener.delete()
            return self.finish(False, "Map data request timeout")
        listener.armTimer()
        self.sendRequest()
        
    def sendRequest(self) -> None:
        mirmsg = MapInformationsRequestMessage()
        mirmsg.init(MapDisplayManager().currentMapPoint.mapId)
        ConnectionsHandler().send(mirmsg)