import collections
import random
import time
from typing import Iterator, Set

from pyd2bot.models.farmPaths.AbstractFarmPath import AbstractFarmPath
from pyd2bot.models.farmPaths.RandomAreaFarmPath import NoTransitionFound
from pyd2bot.thriftServer.pyd2botService.ttypes import Path, TransitionType
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


class RandomSubAreaFarmPath(AbstractFarmPath):
    def __init__(
        self,
        name: str,
        startVertex: Vertex,
        transitionTypeWhitelist: list = None,
    ) -> None:
        super().__init__()
        self.name = name
        self.startVertex = startVertex
        self.transitionTypeWhitelist = transitionTypeWhitelist
        self.subArea = SubArea.getSubAreaByMapId(startVertex.mapId)
        self.verticies = self.reachableVerticies()

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

    def filter_out_transitions(self, edge: Edge, whitelist: list[TransitionTypeEnum]) -> bool:
        for tr in edge.transitions:
            if TransitionTypeEnum(tr.type) not in whitelist:
                edge.transitions.remove(tr)
        return edge
    
    def outgoingEdges(self, vertex=None, onlyNonRecentVisited=False) -> Iterator[Edge]:
        if vertex is None:
            vertex = self.currentVertex
        outgoingEdges = WorldGraph().getOutgoingEdgesFromVertex(vertex)
        ret = []
        for edge in outgoingEdges:
            if edge.dst.mapId in self.subArea.mapIds:
                if self.hasValidTransition(edge):
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
            "transitionTypeWhitelist": self.transitionTypeWhitelist,
        }

    @classmethod
    def from_thriftObj(cls, path: Path) -> "RandomSubAreaFarmPath":
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
        return RandomSubAreaFarmPath(path.id, startVertex, twl)

    def hasValidTransition(self, edge: Edge) -> bool:
        from pydofus2.com.ankamagames.dofus.datacenter.items.criterion.GroupItemCriterion import \
            GroupItemCriterion

        
        if self.transitionTypeWhitelist:
            transitions = [tr for tr in edge.transitions if TransitionTypeEnum(tr.type) in self.transitionTypeWhitelist]
        else:
            transitions = edge.transitions
        
        valid = False
        for transition in transitions:
            
            if transition.criterion:
                if (
                    "&" not in transition.criterion
                    and "|" not in transition.criterion
                    and transition.criterion[0:2] not in AStar.CRITERION_WHITE_LIST
                ):
                    return False
                criterion = GroupItemCriterion(transition.criterion)
                return criterion.isRespected
            valid = True
        return valid
    