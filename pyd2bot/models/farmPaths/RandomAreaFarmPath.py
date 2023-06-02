import collections
import random
import time
from typing import Iterator, Tuple

from pyd2bot.models.farmPaths.AbstractFarmPath import AbstractFarmPath
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
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.pathfinding.Pathfinding import \
    Pathfinding
from pydofus2.com.ankamagames.jerakine.types.positions.MapPoint import MapPoint


class NoTransitionFound(Exception):
    pass
class RandomAreaFarmPath(AbstractFarmPath):
    def __init__(
        self,
        name: str,
        startVertex: Vertex,
        onlyDirections: bool = True,
    ) -> None:
        self.name = name
        self.startVertex = startVertex
        self.area = SubArea.getSubAreaByMapId(startVertex.mapId).area
        self.subAreas = list[SubArea]()
        self.mapIds = set[int]()
        for sa in SubArea.getAllSubArea():
            if sa.areaId == self.area.id:
                self.subAreas.append(sa)
                for mapId in sa.mapIds:
                    self.mapIds.add(mapId)
        self._currentVertex = None
        self._verticies = list[Vertex]()
        self.onlyDirections = onlyDirections
        self._recentVisited = list[Tuple['Vertex', float]]()
        self._transitionBlacklist = list[int]()

    def recentVisitedVerticies(self):
        self._recentVisited = [(_, t) for (_, t) in self._recentVisited if (time.time() - t) < 60 * 5]
        return [v for v, _ in self._recentVisited]
    
    def blackListTransition(self, tr: Transition, edge: Edge):
        self._verticies = None
        self._transitionBlacklist.append(tr)
        
    def __next__(self) -> Tuple[Transition, Edge]:
        outgoingEdges = WorldGraph().getOutgoingEdgesFromVertex(self.currentVertex)
        transitions = list[Tuple[Edge, Transition]]()
        Logger().debug(f"blacklist : {self._transitionBlacklist}")
        for edge in outgoingEdges:
            Logger().debug((edge, AStar.hasValidTransition(edge), edge.dst.mapId in self.mapIds))
            if edge.dst.mapId in self.mapIds:
                if AStar.hasValidTransition(edge):
                    for tr in edge.transitions:
                        if tr in self._transitionBlacklist:
                            continue
                        if self.onlyDirections and TransitionTypeEnum(tr.type) not in [TransitionTypeEnum.INTERACTIVE]:
                            transitions.append((edge, tr))
        notrecent = [(edge, tr) for edge, tr in transitions if edge.dst not in self.recentVisitedVerticies()]
        if notrecent:
            edge, tr = random.choice(notrecent)
        else:
            if len(transitions) == 0:
                raise NoTransitionFound("Couldnt find next transition in path from current vertex.")
            edge, tr = random.choice(transitions)
        self._recentVisited.append((self.currentVertex, time.time()))
        return tr, edge

    def currNeighbors(self) -> Iterator[Vertex]:
        return self.neighbors(self.currentVertex)

    def neighbors(self, vertex: Vertex) -> Iterator[Vertex]:
        outgoingEdges = WorldGraph().getOutgoingEdgesFromVertex(vertex)
        for edge in outgoingEdges:
            if edge.dst.mapId in self.mapIds:
                found = False
                for tr in edge.transitions:
                    if tr.id in self._transitionBlacklist:
                        continue
                    if self.onlyDirections and TransitionTypeEnum(tr.type) not in [TransitionTypeEnum.INTERACTIVE]:
                        found = True
                        break
                if found:
                    yield edge.dst

    @property
    def verticies(self):
        if self._verticies:
            return self._verticies
        queue = collections.deque([self.startVertex])
        self._verticies = set([self.startVertex])
        while queue:
            curr = queue.popleft()
            for v in self.neighbors(curr):
                if v not in self._verticies:
                    queue.append(v)
                    self._verticies.add(v)
        return self._verticies

    def __iter__(self) -> Iterator[Vertex]:
        for it in self.verticies:
            yield it

    def __in__(self, vertex: Vertex) -> bool:
        return vertex in self.verticies

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
        return cls(path.id, startVertex)
