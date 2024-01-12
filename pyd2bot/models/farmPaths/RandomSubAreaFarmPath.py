import collections
import random
import time
from typing import Iterator, Set, Tuple

from pyd2bot.models.farmPaths.AbstractFarmPath import AbstractFarmPath
from pyd2bot.models.farmPaths.RandomAreaFarmPath import NoTransitionFound
from pyd2bot.thriftServer.pyd2botService.ttypes import Path
from pydofus2.com.ankamagames.dofus.datacenter.world.SubArea import SubArea
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.astar.AStar import \
    AStar
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Edge import \
    Edge
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Transition import \
    Transition
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.TransitionTypeEnum import \
    TransitionTypeEnum
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Vertex import \
    Vertex
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.WorldGraph import \
    WorldGraph
from pydofus2.com.ankamagames.jerakine.pathfinding.Pathfinding import \
    Pathfinding
from pydofus2.com.ankamagames.jerakine.types.positions.MapPoint import MapPoint


class RandomSubAreaFarmPath(AbstractFarmPath):
    def __init__(
        self,
        name: str,
        startVertex: Vertex,
        onlyDirections: bool = True,
    ) -> None:
        super().__init__()
        self.name = name
        self.startVertex = startVertex
        self.subArea = SubArea.getSubAreaByMapId(startVertex.mapId)
        self.verticies = self.reachableVerticies()
        self.noInteractive = onlyDirections

    def recentVisitedVerticies(self):
        self._recent_visited = [(_, time_added) for (_, time_added) in self._recent_visited if (time.time() - time_added) < 60 * 5]
        return [v for v, _ in self._recent_visited]
    
    def __next__(self, forbidenEdges) -> Edge:
        outgoingEdges = list(self.outgoingEdges(onlyNonRecentVisited=True))
        outgoingEdges = [e for e in outgoingEdges if e not in forbidenEdges]
        if not outgoingEdges:
            raise NoTransitionFound()
        edge = random.choice(outgoingEdges)
        return edge

    def currNeighbors(self) -> Iterator[Vertex]:
        return self.outgoingEdges(self.currentVertex)

    def outgoingEdges(self, vertex=None, onlyNonRecentVisited=False) -> Iterator[Edge]:
        if vertex is None:
            vertex = self.currentVertex
        outgoingEdges = WorldGraph().getOutgoingEdgesFromVertex(vertex)
        ret = []
        for edge in outgoingEdges:
            if edge.dst.mapId in self.subArea.mapIds and AStar.hasValidTransition(edge):
                if onlyNonRecentVisited:
                    if edge.dst in self.lastVisited:
                        if time.perf_counter() - self.lastVisited[edge.dst] > 60 * 60:
                            ret.append(edge)
                    else:
                        ret.append(edge)
                else:
                    ret.append(edge)
        return ret
    
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

    def __iter__(self) -> Iterator[Vertex]:
        for it in self.verticies:
            yield it

    def __in__(self, vertex: Vertex) -> bool:
        return vertex in self.verticies

    def to_json(self) -> dict:
        return {
            "type": self.__class__.__name__,
            "name": self.name,
            "subAreaId": self.subArea.id,
            "startVertex": {
                "mapId": self.startVertex.mapId,
                "mapRpZone": self.startVertex.zoneId,
            },
        }

    @classmethod
    def from_thriftObj(cls, path: Path) -> "RandomSubAreaFarmPath":
        startVertex = WorldGraph().getVertex(path.startVertex.mapId, path.startVertex.zoneId)
        if startVertex is None:
            raise ValueError("Could not find start vertex from startVertex : " + str(path.startVertex))
        return cls(path.id, startVertex)
