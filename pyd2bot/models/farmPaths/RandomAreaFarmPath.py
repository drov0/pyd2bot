import collections
import random
import time
from typing import Iterator, List, Set, Tuple

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
        self.subAreas = self.getAllSubAreas()
        self.mapIds = self.getAllMapsIds()
        self.verticies = self.getAllReachableVerticies()
        self.visited = collections.defaultdict(int) 
        self.onlyDirections = onlyDirections
        self._transitionBlacklist = list[int]()
    
    def getNext(self, reward=1) -> Tuple[Transition, Edge]:
        currVertes = self.currentVertex
        if not currVertes:
            raise NoTransitionFound("Couldn't find current vertex.")
        transitions = self.getOutgoingTransitions()
        if not transitions:
            raise NoTransitionFound("Couldn't find next transition in path from current vertex.")
        # TODO: here integrate Q-Learning approach
    
    def outGoingEdges(self, vertex: Vertex) -> Iterator[Edge]:
        outgoingEdges = WorldGraph().getOutgoingEdgesFromVertex(vertex)
        for edge in outgoingEdges:
            if edge.dst.mapId in self.mapIds and AStar.hasValidTransition(edge):
                possibleTransitions = []
                for tr in edge.transitions:
                    if tr not in self._transitionBlacklist and (not self.onlyDirections or TransitionTypeEnum(tr.type) not in [TransitionTypeEnum.INTERACTIVE]):
                        possibleTransitions.append(tr)
                if possibleTransitions:
                    yield edge, possibleTransitions
                    
    def getOutgoingTransitions(self) -> List[Tuple[Edge, Transition]]:
        transitions = list()
        for edge, ptrs in self.outGoingEdges(self.currentVertex):
            for tr in ptrs:
                transitions.append((edge, tr))
        return transitions
    
    def getAllReachableVerticies(self) -> Set[Vertex]:
        queue = collections.deque([self.startVertex])
        verticies = set([self.startVertex])
        while queue:
            curr = queue.popleft()
            for e in self.outGoingEdges(curr):
                if e.dst not in verticies:
                    queue.append(e.dst)
                    verticies.add(e.dst)
        return verticies
        
    def __iter__(self) -> Iterator[Vertex]:
        for it in self.verticies:
            yield it

    def __in__(self, vertex: Vertex) -> bool:
        return vertex in self.verticies
    
    def blackListTransition(self, tr: Transition, edge: Edge):
        self._transitionBlacklist.append(tr)
        self.verticies = self.getAllReachableVerticies()
    
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
        return cls(path.id, startVertex)
