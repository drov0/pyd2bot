


from typing import Tuple

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.AutoTrip import AutoTrip
from pyd2bot.logic.roleplay.behaviors.UseZaap import UseZaap
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.datacenter.world.Hint import Hint
from pydofus2.com.ankamagames.dofus.datacenter.world.SubArea import SubArea
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.common.managers.PlayerManager import \
    PlayerManager
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.astar.AStar import \
    AStar
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Vertex import \
    Vertex
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.WorldGraph import \
    WorldGraph
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


class AutoTripUseZaap(AbstractBehavior):

    _allZaapMapIds: list[int] = None
    
    def __init__(self) -> None:
        super().__init__()

    def run(self, dstMapId, dstZoneId=1):
        self.dstMapId = dstMapId        
        self.dstZoneId = dstZoneId
        KernelEventsManager().on(KernelEvent.TEXT_INFO, self.onServerInfo, originator=self)
        self.dstZaapMapId = SubArea.getSubAreaByMapId(dstMapId).associatedZaapMapId
        self.havreSacMapListener = None
        if not PlayedCharacterManager().isZaapKnown(self.dstZaapMapId):
            Logger().debug(f"Dest zaap is not known will travel to register it.")
            return AutoTrip().start(self.dstZaapMapId, self.dstZoneId, callback=self.onDstZaapTrip, parent=self)
        self.dstVertex = WorldGraph().getVertex(self.dstMapId, self.dstZoneId)
        self.dstZaapVertex, self.dstZaapDist = self.findDistFrom(self.dstVertex, self.dstZaapMapId)
        Logger().debug(f"Dest Zaap is at '{self.dstZaapDist}' steps.")
        if PlayerManager().isBasicAccount():
            self.srcZaapMapId = PlayedCharacterManager().currentSubArea.associatedZaapMapId
            self.srcZaapVertex, self.srcZaapDist = self.findDistFrom(PlayedCharacterManager().currVertex, self.srcZaapMapId)            
            Logger().debug(f"Src Zaap is at '{self.srcZaapDist}' steps.")
        else:
            self.srcZaapDist = 0
        self.dstVertex, self.distFromTarget = self.findDistFrom(PlayedCharacterManager().currVertex, dstMapId, maxLen=self.srcZaapDist + self.dstZaapDist)
        Logger().debug(f"Dest Map is at '{self.distFromTarget}' steps.")
        if self.distFromTarget <= self.srcZaapDist + self.dstZaapDist:
            AutoTrip().start(self.dstVertex.mapId, self.dstVertex.zoneId, callback=self.finish, parent=self)
        elif PlayerManager().isBasicAccount():
            AutoTrip().start(self.srcZaapVertex.mapId, self.srcZaapVertex.zoneId, callback=self.onSrcZaapTrip, parent=self)
        else:
            self.enterHavreSac(self.onSrcZaapTrip)

    def enterHavreSac(self, callback):
        self.havreSacMapListener = KernelEventsManager().onceMapProcessed(
            callback=callback,
            originator=self,
        )
        return Kernel().roleplayContextFrame.havenbagEnter()
    
    def onServerInfo(self, event, msgId, msgType, textId, msgContent, params):
        if textId == 589088: # Can't join havresac from current Map
            if self.havreSacMapListener:
                self.havreSacMapListener.delete()
                
    def onDstZaapTrip(self, code, err):
        if err:
            if code == UseZaap.NOT_RICH_ENOUGH:
                Logger().warning(err)
                if PlayerManager().isBasicAccount():
                    AutoTrip().start(self.dstMapId, self.dstZoneId, callback=self.finish, parent=self)
                elif PlayerManager().isMapInHavenbag(PlayedCharacterManager().currentMap.mapId):
                    self.enterHavreSac(lambda: AutoTrip().start(self.dstMapId, self.dstZoneId, callback=self.finish, parent=self))
            else:
                return self.finish(code, err)
        AutoTrip().start(self.dstMapId, self.dstZoneId, callback=self.finish, parent=self)
        
    def onSrcZaapTrip(self, code=1, err=None):
        if err:
            return self.finish(code, err)
        UseZaap().start(self.dstZaapVertex.mapId, callback=self.onDstZaapTrip, parent=self)
    
    @classmethod
    def findDistFrom(cls, srcV: Vertex, mapId, maxLen=float("inf")) -> Tuple[Vertex, int]:
        if mapId == srcV.mapId:
            return srcV, 0       
        rpZ = 1
        minDist = float("inf")
        vertex = None
        while True:
            dstV = WorldGraph().getVertex(mapId, rpZ)
            if not dstV:
                break
            path = AStar().search(WorldGraph(), srcV, dstV, maxPathLength=min(maxLen, minDist))
            if path is not None:
                dist = len(path)
                if dist < minDist:
                    minDist = dist
                    vertex = dstV
            rpZ += 1
        return vertex, minDist 
