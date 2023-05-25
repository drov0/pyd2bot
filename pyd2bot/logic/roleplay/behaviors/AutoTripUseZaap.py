


from typing import Tuple
from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.AutoTrip import AutoTrip
from pyd2bot.logic.roleplay.behaviors.UseZaap import UseZaap
from pydofus2.com.ankamagames.dofus.datacenter.world.Hint import Hint
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.astar.AStar import \
    AStar
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Vertex import \
    Vertex
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.WorldGraph import \
    WorldGraph


class AutoTripUseZaap(AbstractBehavior):

    _allZaapMapIds: list[int] = None
    def __init__(self) -> None:
        super().__init__()

    def run(self, dstMapId, dstZoneId=1):
        self.dstMapId = dstMapId
        self.dstZoneId = dstZoneId
        self.dstZaapVertex, self.dstZaapDist = self.findClosestZaap(self.dstMapId)
        if not Kernel().zaapFrame.isZaapKnown(self.dstZaapVertex.mapId):
            return AutoTrip().start(self.dstZaapVertex.mapId, self.dstZaapVertex.zoneId, callback=self.finish, parent=self)
        self.srcZaapVertex, self.srcZaapDis = self.findClosestZaap(PlayedCharacterManager().currentMap.mapId)
        self.dstVertex, self.distFromTarget = self.findDistFrom(PlayedCharacterManager().currVertex, dstMapId, maxLen=self.srcZaapDis + self.dstZaapDist)
        if self.distFromTarget <= self.srcZaapDis + self.dstZaapDist:
            AutoTrip().start(self.dstVertex.mapId, self.dstVertex.zoneId, callback=self.finish, parent=self)
        else:
            AutoTrip().start(self.srcZaapVertex.mapId, self.srcZaapVertex.zoneId, callback=self.onSrcZaapTrip, parent=self)

    def onDstZaapTrip(self, code, err):
        if err:
            return self.finish(code, err)
        AutoTrip().start(self.dstMapId, self.dstZoneId, callback=self.finish, parent=self)
        
    def onSrcZaapTrip(self, code, err):
        if err:
            return self.finish(code, err)
        UseZaap().start(self.dstMapId, callback=self.onDstZaapTrip, parent=self)
    
    @classmethod
    def getAllZaapMapIds(cls):
        ret = []
        hints = Hint.getHints()
        for h in hints:
            if h.name == "Zaap":
                ret.append(h.mapId)
        return ret
    
    @classmethod
    def findDistFrom(cls, srcV: Vertex, mapId, maxLen=None) -> Tuple[Vertex, int]:
        if mapId == srcV.mapId:
            return 0       
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

    @classmethod
    def findClosestZaap(cls, tgtMapId) -> Tuple[Vertex, int]:
        if cls._allZaapMapIds is None:
            cls._allZaapMapIds = cls.getAllZaapMapIds()       
        minDist = float("inf")
        tgrRpz = 1
        result = None
        while True:
            srcV = WorldGraph().getVertex(tgtMapId, tgrRpz)
            if not srcV:
                break
            for mapId in AutoTripUseZaap._allZaapMapIds:
                dist, vertex = cls.findDistFrom(srcV, mapId)
                if dist < minDist:
                    minDist = dist
                    result = vertex
            tgrRpz += 1
        return result, minDist