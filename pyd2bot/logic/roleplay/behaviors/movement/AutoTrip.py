from enum import Enum
from time import perf_counter

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.movement.ChangeMap import ChangeMap
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.types.MovementFailError import \
    MovementFailError
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.astar.AStar import \
    AStar
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Edge import \
    Edge
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.WorldGraph import \
    WorldGraph
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


class AutoTripState(Enum):
    IDLE = 0
    CALCULATING_PATH = 1
    FOLLOWING_EDGE = 2

class AutoTrip(AbstractBehavior):
    NO_PATH_FOUND = 2202203
    
    def __init__(self):
        super().__init__()
        self.path = None
        self.state = AutoTripState.IDLE        
        self.dstMapId = None
        self.dstRpZone = None
        
    def run(self, dstMapId, dstZoneId, path: list[Edge]=None):
        self.dstMapId = dstMapId
        self.dstRpZone = dstZoneId
        self.path = path
        AStar().resetForbinedEdges()
        self.walkToNextStep()

    def currentEdgeIndex(self):
        v = PlayedCharacterManager().currVertex
        for i, step in enumerate(self.path):
            if step.src.UID == v.UID:
                return i

    def walkToNextStep(self, event_id=None):
        if PlayedCharacterManager().currentMap is None:
            Logger().warning("Waiting for Map to be processed...")
            return KernelEventsManager().onceMapProcessed(self.walkToNextStep, originator=self)
        if self.path:
            self.state = AutoTripState.FOLLOWING_EDGE
            currMapId = PlayedCharacterManager().currVertex.mapId
            dstMapId = self.path[-1].dst.mapId
            if currMapId == dstMapId:
                Logger().info(f"Trip reached destination Map : {dstMapId}")
                return self.finish(True, None)
            currentIndex = self.currentEdgeIndex()
            if currentIndex is None:
                return self.findPath(self.dstMapId, self.dstRpZone, self.onPathFindResul)
            Logger().debug(f"Current step index: {currentIndex + 1}/{len(self.path)}")
            nextEdge = self.path[currentIndex]
            Logger().debug(f"Moving using next edge :")
            Logger().debug(f"\t|- src {nextEdge.src.mapId} -> dst {nextEdge.dst.mapId}")
            for tr in nextEdge.transitions:
                Logger().debug(f"\t| => {tr}")
            def onProcessed(code, error):
                if error:
                    if code in [MovementFailError.CANT_REACH_DEST_CELL, MovementFailError.MAPCHANGE_TIMEOUT, MovementFailError.NOMORE_SCROLL_CELL]:
                        Logger().warning(f"Can't reach next step in found path for reason : {code.name}")
                        AStar().addForbidenEdge(nextEdge)
                        return self.findPath(self.dstMapId, self.dstRpZone, self.onPathFindResul)
                    else:
                        return self.finish(code, error)
                self.walkToNextStep()
            self.changeMap(edge=nextEdge, callback=onProcessed)
        else:
            self.state = AutoTripState.CALCULATING_PATH
            self.findPath(self.dstMapId, self.dstRpZone, self.onPathFindResul)
    
    def onPathFindResul(self, path, error):
        if error:
            return self.finish(path, error)
        if len(path) == 0:
            return self.finish(True, None)
        for e in path:
            Logger().debug(f"\t|- src {e.src.mapId} -> dst {e.dst.mapId}")
            for tr in e.transitions:
                Logger().debug(f"\t\t|- {tr}")
        self.path = path
        self.walkToNextStep()
        
    def findPath(self, dst: float, linkedZone: int, callback) -> None:
        if linkedZone is None:
            linkedZone = 1
        src = PlayedCharacterManager().currVertex
        if src is None:
            return self.onceMapProcessed(self.findPath, [dst, linkedZone, callback])
        Logger().info(
            f"[WoldPathFinder] Start searching path from {src} to destMapId {dst}"
        )
        if PlayedCharacterManager().currentMap.mapId == dst:
            return callback([], None)
        while True:        
            dstV = WorldGraph().getVertex(dst, linkedZone)            
            if dstV is None:
                return callback(self.NO_PATH_FOUND, "Unable to find path to dest map")
            start = perf_counter()
            path = AStar().search(WorldGraph(), src, dstV)
            if path:
                Logger().info(f"[WoldPathFinder] Path to map {str(dst)} found in {perf_counter() - start}s")
                return callback(path, None)
            linkedZone += 1

    def getState(self):
        return self.state.name