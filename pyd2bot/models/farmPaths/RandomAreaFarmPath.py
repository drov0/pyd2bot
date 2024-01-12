import collections
import random
from time import perf_counter
from typing import Iterator, Set

from pyd2bot.models.farmPaths.AbstractFarmPath import AbstractFarmPath
from pyd2bot.thriftServer.pyd2botService.ttypes import Path, TransitionType
from pydofus2.com.ankamagames.dofus.datacenter.world.MapPosition import \
    MapPosition
from pydofus2.com.ankamagames.dofus.datacenter.world.SubArea import SubArea
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.astar.AStar import \
    AStar
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Edge import \
    Edge
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.TransitionTypeEnum import \
    TransitionTypeEnum
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Vertex import \
    Vertex
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.WorldGraph import \
    WorldGraph
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


class NoTransitionFound(Exception):
    pass
class RandomAreaFarmPath(AbstractFarmPath):
    
    def __init__(
        self,
        name: str,
        startVertex: Vertex,
        transitionTypeWhitelist: list = None,
    ) -> None:
        super().__init__()
        self.name = name
        self.startVertex = startVertex
        self.transitionTypeWhitelist: list[TransitionTypeEnum] = transitionTypeWhitelist

        self.area = SubArea.getSubAreaByMapId(startVertex.mapId).area
        self.subAreas = self.getAllSubAreas()
        self.mapIds = self.getAllMapsIds()
        self.verticies = self.reachableVerticies()

    @property
    def pourcentExplored(self):
        return 100 * len(self.lastVisited) / len(self.verticies)

    def getClosestUnvisited(self):
        bestDist = float("inf")
        bestSolution = None
        currMp = MapPosition.getMapPositionById(self.currentVertex.mapId)
        for v in self.verticies:
            if v.mapId == self.currentVertex.mapId:
                continue
            if v not in self.lastVisited:
                vMp = MapPosition.getMapPositionById(v.mapId)
                dist = abs(currMp.posX - vMp.posX) + abs(currMp.posY - vMp.posY)
                if dist < bestDist:
                    bestDist = dist
                    bestSolution = v
        if bestSolution is None:
            Logger().error(f"No unvisited vertex found")
        return bestSolution
    
    def __next__(self, forbidenEdges) -> Edge:
        outgoingEdges = list(self.outgoingEdges(onlyNonRecentVisited=True))
        outgoingEdges = [e for e in outgoingEdges if e not in forbidenEdges]
        if not outgoingEdges:
            raise NoTransitionFound()
        edge = random.choice(outgoingEdges)
        return edge
    
    def reachableVerticies(self) -> Set[Vertex]:
        queue = collections.deque([self.startVertex])
        verticies = set([self.startVertex])
        while queue:
            curr = queue.popleft()
            for e in self.outgoingEdges(curr):
                if e.dst not in verticies:
                    queue.append(e.dst)
                    verticies.add(e.dst)
        return verticies

    def filter_out_transitions(self, edge: Edge, tr_types_whitelist: list[TransitionTypeEnum]) -> bool:
        for tr in edge.transitions:
            if TransitionTypeEnum(tr.type) not in tr_types_whitelist:
                edge.transitions.remove(tr)
        return edge
            
    def outgoingEdges(self, vertex=None, onlyNonRecentVisited=False) -> Iterator[Edge]:
        if vertex is None:
            vertex = self.currentVertex
        outgoingEdges = WorldGraph().getOutgoingEdgesFromVertex(vertex)
        ret = []
        for edge in outgoingEdges:
            if edge.dst.mapId in self.mapIds:
                if self.transitionTypeWhitelist:
                    edge = edge.clone()
                    edge = self.filter_out_transitions(edge, self.transitionTypeWhitelist)
                if AStar.hasValidTransition(edge):
                    if onlyNonRecentVisited:
                        if edge.dst in self.lastVisited:
                            if perf_counter() - self.lastVisited[edge.dst] > 60 * 60:
                                ret.append(edge)
                        else:
                            ret.append(edge)
                    else:
                        ret.append(edge)
        return ret
    
    def __iter__(self) -> Iterator[Vertex]:
        for it in self.verticies:
            yield it

    def __in__(self, vertex: Vertex) -> bool:
        return vertex in self.verticies
    
    def getAllSubAreas(self):
        subAreas = []
        for sa in SubArea.getAllSubArea():
            if sa.areaId == self.area.id:
                subAreas.append(sa)
        return subAreas
    
    def getAllMapsIds(self) -> Set[int]:
        mapIds = set[int]()
        for sa in self.subAreas:
            for mapId in sa.mapIds:
                mapIds.add(mapId)
        return mapIds

    def to_json(self) -> dict:
        return {
            "type": self.__class__.__name__,
            "name": self.name,
            "areaId": self.area.id,
            "startVertex": {
                "mapId": self.startVertex.mapId,
                "mapRpZone": self.startVertex.zoneId,
            },
        }

    @classmethod
    def from_thriftObj(cls, path: Path) -> "RandomAreaFarmPath":
        startVertex = WorldGraph().getVertex(path.startVertex.mapId, path.startVertex.zoneId)
        if startVertex is None:
            raise ValueError("Could not find start vertex from startVertex : " + str(path.startVertex))
        twl = None
        if path.transitionTypeWhitelist:
            twl = []
            for e in path.transitionTypeWhitelist:
                if e == TransitionType.SCROLL:
                    twl.append(TransitionTypeEnum.SCROLL)
                elif e == TransitionType.SCROLL_ACTION:
                    twl.append(TransitionTypeEnum.SCROLL_ACTION)
                elif e == TransitionType.INTERACTIVE:
                    twl.append(TransitionTypeEnum.INTERACTIVE)
                elif e == TransitionType.MAP_ACTION:
                    twl.append(TransitionTypeEnum.MAP_ACTION)
                elif e == TransitionType.MAP_EVENT:
                    twl.append(TransitionTypeEnum.MAP_EVENT)
                elif e == TransitionType.MAP_OBSTACLE:
                    twl.append(TransitionTypeEnum.MAP_OBSTACLE)
        return cls(path.id, startVertex, twl)
