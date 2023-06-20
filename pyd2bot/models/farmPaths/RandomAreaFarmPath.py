import collections
import datetime
import os
import pickle
import random
import threading
import time
from typing import Iterator, List, Set, Tuple

import numpy as np
from matplotlib import pyplot as plt

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


class NoTransitionFound(Exception):
    pass
class RandomAreaFarmPath(AbstractFarmPath):
    
    def __init__(
        self,
        name: str,
        startVertex: Vertex
    ) -> None:
        super().__init__()
        self.name = name
        self.startVertex = startVertex
        self.area = SubArea.getSubAreaByMapId(startVertex.mapId).area
        self.subAreas = self.getAllSubAreas()
        self.mapIds = self.getAllMapsIds()
        self.verticies = self.reachableVerticies()
        self.visited = set()

    @property
    def pourcentExplored(self):
        return 100 * len(self.visited) / len(self.verticies)

    def outgoingEdges(self, vertex=None) -> Iterator[Edge]:
        if vertex is None:
            vertex = self.currentVertex
        outgoingEdges = WorldGraph().getOutgoingEdgesFromVertex(vertex)
        for edge in outgoingEdges:
            if edge.dst.mapId in self.mapIds and AStar.hasValidTransition(edge):
                yield edge
    
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
