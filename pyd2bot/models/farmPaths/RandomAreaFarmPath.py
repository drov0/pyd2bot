import collections
import random
import time
from typing import Iterator, List, Tuple

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
        exploration_prob: float = 0.7,
        epsilon_decay: float = 0.995,
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
        self._verticies = None
        self._currentVertex = None
        self._visited = collections.defaultdict(int) 
        self.onlyDirections = onlyDirections
        self._transitionBlacklist = list[int]()
        
        self.exploration_prob = exploration_prob
        self.epsilon_decay = epsilon_decay
    
    def blackListTransition(self, tr: Transition, edge: Edge):
        self._verticies = None
        self._transitionBlacklist.append(tr)
    
    def getOutgoingTransitions(self) -> List[Tuple[Transition, Edge]]:
        outgoingEdges = WorldGraph().getOutgoingEdgesFromVertex(self.currentVertex)
        transitions = list[Tuple[Edge, Transition]]()
        for edge in outgoingEdges:
            if edge.dst.mapId in self.mapIds and AStar.hasValidTransition(edge):
                for tr in edge.transitions:
                    if tr in self._transitionBlacklist:
                        continue
                    if self.onlyDirections and TransitionTypeEnum(tr.type) not in [TransitionTypeEnum.INTERACTIVE]:
                        transitions.append((edge, tr))
        return transitions
    
    def getNext(self, reward=1) -> Tuple[Transition, Edge]:
        transitions = self.getOutgoingTransitions()
        if not transitions:
            raise NoTransitionFound("Couldn't find next transition in path from current vertex.")

        # Update the reward for the current vertex based on the resources collected
        self._visited[self._currentVertex] += reward

        if random.random() < self.exploration_prob:
            # With probability exploration_prob, take a random transition
            edge, tr = random.choice(transitions)
        else:
            # With probability 1 - exploration_prob, take the most rewarding transition
            edge, tr = max(transitions, key=lambda trans: self._visited.get(trans[0].dst, 0))

        self._visited[edge.dst] += reward

        # Decay the exploration probability
        self.exploration_prob *= self.epsilon_decay

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
