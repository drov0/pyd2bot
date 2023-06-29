import time
import numpy as np
from pyd2bot.logic.roleplay.behaviors.farm.CollectableResource import (
    CollectableResource,
)
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import (
    PlayedCharacterManager,
)
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Edge import Edge
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Vertex import Vertex


class ResourceFarmerState:
    MAX_RESOURCES = 20
    MAX_NEIGHBORS = 8
    ACTION_SIZE = 28
    STATE_SIZE = 2 + 5 * 4 + 2 + MAX_RESOURCES * 5 + MAX_NEIGHBORS * 4

    def __init__(
        self,
        vertex: Vertex = None,
        resources: list[CollectableResource] = None,
        outgoingEdges: list[Edge] = None,
        lastTimeVertexVisited: dict[Vertex, int] = None,
        lastTimeResourceCollected: dict[int, int] = None,
        nbrVertexVisites: dict = None,
        jobFilter=None,
        jobImportance=None,
        forbiddenActions=None,
    ) -> None:
        self.vertex = vertex
        self.resources = resources
        self.outgoingEdges = outgoingEdges
        self.lastTimeVertexVisited = lastTimeVertexVisited
        self.lastTimeResourceCollected = lastTimeResourceCollected
        self.nbrVertexVisites = nbrVertexVisites
        self.jobFilter = jobFilter
        self.jobImportance = jobImportance
        self.forbiddenActions = forbiddenActions
        self._representation = None

    def action_size(self):
        return self.ACTION_SIZE

    def state_size(self):
        return self.STATE_SIZE

    def resource_representation(self, resource: CollectableResource):
        return [
            resource.resourceId,
            int(resource.canFarm(self.jobFilter)),
            resource.jobId,
            resource.distance,
        ]

    def vertex_representation(self, vertex: Vertex):
        return [vertex.mapId, vertex.zoneId]

    def represent(self):
        if self._representation is None:
            state_repr = []
            state_repr.append(PlayedCharacterManager().limitedLevel)
            if PlayedCharacterManager().inventoryWeightMax != 0:
                state_repr.append(
                    PlayedCharacterManager().inventoryWeight
                    / PlayedCharacterManager().inventoryWeightMax
                )
            else:
                state_repr.append(-1)

            # Add jobs representation
            for jobId in self.jobImportance:
                job = PlayedCharacterManager().jobs.get(jobId)
                if job:
                    state_repr.append(jobId)
                    state_repr.append(job.jobLevel)
                    state_repr.append(
                        (job.jobXP - job.jobXpLevelFloor)
                        / (job.jobXpNextLevelFloor - job.jobXpLevelFloor)
                    )
                    state_repr.append(self.jobImportance[jobId])
                else:
                    state_repr.extend([0, 0, 0, 0])

            # Add vertex representation
            state_repr.extend(self.vertex_representation(self.vertex))

            # Add resources representation
            for i in range(self.MAX_RESOURCES):
                if i < len(self.resources):
                    state_repr.extend(self.resource_representation(self.resources[i]))
                    if self.resources[i].uid in self.lastTimeResourceCollected:
                        timeSinceLastCollect = (
                            time.time()
                            - self.lastTimeResourceCollected[self.resources[i].uid]
                        ) // 60
                    else:
                        timeSinceLastCollect = -1
                    state_repr.append(timeSinceLastCollect)
                else:
                    state_repr.extend([0, 0, 0, 0, 0])  # Padding for missing resources

            # Add neighbors representation
            for i in range(self.MAX_NEIGHBORS):
                if i < len(self.outgoingEdges):
                    dstV = self.outgoingEdges[i].dst
                    state_repr.extend(self.vertex_representation(dstV))
                    state_repr.append(self.nbrVertexVisites.get(dstV, 0))
                    if dstV in self.lastTimeVertexVisited:
                        timeSinceLastInteraction = (
                            time.time() - self.lastTimeVertexVisited[dstV]
                        ) // 60
                    else:
                        timeSinceLastInteraction = -1
                    state_repr.append(timeSinceLastInteraction)
                else:
                    state_repr.extend([0, 0, 0, 0])  # Padding for missing neighbors

            self._representation = np.array(state_repr)

        return self._representation

    def getFarmableResources(self):
        return [r for r in self.resources if r.canFarm(self.jobFilter) and r not in self.forbiddenActions]
    
    def getAction(self, actionIndex):
        if actionIndex < self.MAX_RESOURCES:
            if actionIndex < len(self.resources):
                return self.resources[actionIndex]
            else:
                return None
        else:
            index = actionIndex - self.MAX_RESOURCES
            if index < len(self.outgoingEdges):
                return self.outgoingEdges[index]
            else:
                return None

    def getValidAction(self, q_values):
        # Create a mask of valid actions
        valid_actions_mask = np.zeros_like(q_values)
        num_resources = min(len(self.resources), self.MAX_RESOURCES)
        num_outgoing_edges = min(len(self.outgoingEdges), self.MAX_NEIGHBORS)

        # Mark the valid resource actions as 1
        for resource_index in range(num_resources):
            r = self.resources[resource_index]
            if r.uid not in self.forbiddenActions and r.canFarm(self.jobFilter):
                valid_actions_mask[resource_index] = 1

        # Mark the valid vertex actions as 1
        for edge_index in range(num_outgoing_edges):
            e = self.outgoingEdges[edge_index]
            if e not in self.forbiddenActions:
                valid_actions_mask[self.MAX_RESOURCES + edge_index] = 1

        # Apply the mask to the q_values
        valid_q_values = np.where(valid_actions_mask, q_values, -np.inf)

        # Return the action with maximum Q-value among valid actions
        res = np.argmax(valid_q_values)

        assert (
            0 <= res < num_resources
            or self.MAX_RESOURCES <= res < self.MAX_RESOURCES + num_outgoing_edges
        )
        assert res < self.ACTION_SIZE
        return res

    def getRandomValidAction(self):
        # Create a list of valid actions
        valid_actions = []
        num_resources = min(len(self.resources), self.MAX_RESOURCES)
        num_edges = min(len(self.outgoingEdges), self.MAX_NEIGHBORS)

        non_forbidden_indices = [
            idx
            for idx in range(num_edges)
            if self.outgoingEdges[idx] not in self.forbiddenActions
        ]
        
        vertex_visits = np.array([
            self.nbrVertexVisites.get(edge.dst, 0) for edge in self.outgoingEdges
        ])

        # Restrict the vertex visits array to non-forbidden indices
        non_forbidden_vertex_visits = vertex_visits[non_forbidden_indices]

        # Get the index of the edge with minimum visits
        min_visits_idx = np.argmin(non_forbidden_vertex_visits)

        # Translate this back into the original indices
        min_visits_edge_idx = non_forbidden_indices[min_visits_idx] + self.MAX_RESOURCES

        # Add valid resource actions
        for resource_index in range(num_resources):
            r = self.resources[resource_index]
            if r.uid not in self.forbiddenActions and r.canFarm(self.jobFilter):
                valid_actions.append(resource_index)

        # Add valid vertex actions weighted by their visits
        valid_actions.append(min_visits_edge_idx)

        # Randomly choose an action from valid actions
        res = np.random.choice(valid_actions)
        assert (
            0 <= res < num_resources
            or self.MAX_RESOURCES <= res < self.MAX_RESOURCES + len(self.outgoingEdges)
        )
        assert res < self.ACTION_SIZE
        return res
