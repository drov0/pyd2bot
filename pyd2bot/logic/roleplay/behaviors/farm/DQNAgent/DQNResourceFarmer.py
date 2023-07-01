import collections
import os
import pickle
import random
import time
from typing import cast

import numpy as np
from prettytable import PrettyTable
import tensorflow as tf

from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.AbstractFarmBehavior import AbstractFarmBehavior
from pyd2bot.logic.roleplay.behaviors.farm.CollectableResource import (
    CollectableResource,
)
from pyd2bot.logic.roleplay.behaviors.farm.DQNAgent.DQNAgent import DQNAgent
from pyd2bot.logic.roleplay.behaviors.farm.DQNAgent.ResourceFarmerState import (
    ResourceFarmerState,
)
from pyd2bot.logic.roleplay.behaviors.movement.AutoTrip import AutoTrip
from pyd2bot.logic.roleplay.behaviors.movement.ChangeMap import ChangeMap
from pyd2bot.logic.roleplay.behaviors.skill.UseSkill import UseSkill
from pyd2bot.models.farmPaths.RandomAreaFarmPath import RandomAreaFarmPath
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.dofus.datacenter.jobs.Job import Job
from pydofus2.com.ankamagames.dofus.internalDatacenter.items.ItemWrapper import (
    ItemWrapper,
)
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.types.MovementFailError import (
    MovementFailError,
)
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Edge import Edge
from pydofus2.com.ankamagames.dofus.network.types.game.context.roleplay.job.JobExperience import (
    JobExperience,
)
from pydofus2.com.ankamagames.jerakine.benchmark.BenchmarkTimer import BenchmarkTimer
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

CURR_DIR = os.path.dirname(os.path.abspath(__file__))


class DQNResourceFarm(AbstractFarmBehavior):
    JOB_IMPORTANCE = {
        36: 8,  # fisher
        2: 17,  # woodshoper,
        26: 12,  # alchimist
        28: 8,  # farmer
        24: 200,  # miner
    }

    def __init__(
        self,
        timeout=None,
    ):
        super().__init__(timeout)
        self.rewards = []
        self.explorationPercentages = []
        self.currentVertex = None
        self.stateFile = os.path.join(CURR_DIR, f"{Logger().prefix}_state.pkl")
        self.modelFile = os.path.join(CURR_DIR, f"{Logger().prefix}_agent_model")
        self.areaScrappingFile = os.path.join(CURR_DIR, f"Area_Data.pkl")
        self.jobFilter = BotConfig().jobFilter
        self.path: RandomAreaFarmPath = BotConfig().path
        self.forbidenActions = set()
        self.availableResources = None
        self.outgoingEdges = None
        self.gainedJobExperience = {}
        self.gainedJobLevel = {}
        self.gainedKamas = {}
        self.agent = DQNAgent()
        self.lastState: ResourceFarmerState = None
        self.currentState: ResourceFarmerState = None
        self.lastTimeVertexVisited = {}
        self.lastTimeResourceCollected = {}
        self.nbrVertexVisites = {}
        self.collected = set()
        self.respawnTimeRecords = {}
        self.discovered = {}
        self.nonFarmable = set()
        self.lastTimeSentToRandVertex = None
        self.timeSpentFarming = 0
        self.timeSpentChangingMap = 0
        self.timeFarmerStarted = 0
        self.timeSpentLearning = 0
        self.areaScrapping = {}
        self.loadAgentState()
        Logger().debug(f"Qresource farm initialized")

    def init(self):
        if not self.timeFarmerStarted:
            self.timeFarmerStarted = time.time()
        return True

    def onObjectAdded(self, event, iw: ItemWrapper):
        if "sac de " in iw.name.lower():
            return Kernel().inventoryManagementFrame.useItem(iw)

    def onJobLevelUp(self, event, jobId, jobName, lastJobLevel, newLevel, podsBonus):
        if jobId not in self.gainedJobLevel:
            self.gainedJobLevel[jobId] = 0
        self.gainedJobLevel[jobId] += newLevel - lastJobLevel

    def onJobExperience(self, event, oldJobXp, jobExperience: JobExperience):
        xpPourcent = (
            100
            * (jobExperience.jobXP - oldJobXp)
            / (jobExperience.jobXpNextLevelFloor - jobExperience.jobXpLevelFloor)
        )
        job = Job.getJobById(jobExperience.jobId)
        Logger().debug(f"Job {job.name} gained {xpPourcent:.2f}% experince")
        if jobExperience.jobId not in self.gainedJobExperience:
            self.gainedJobExperience[jobExperience.jobId] = 0
        self.gainedJobExperience[jobExperience.jobId] += xpPourcent

    def onObtainedItem(self, event, iw: ItemWrapper, qty):
        averageKamasWon = (
            Kernel().averagePricesFrame.getItemAveragePrice(iw.objectGID) * qty
        )
        self.gainedKamas += averageKamasWon

    def getCollecteReward(self):
        investedTime = time.time() - self.actionStartTime
        self.timeSpentFarming += investedTime
        jobxp = sum(
            self.gainedJobExperience.get(jobId, 0) * self.JOB_IMPORTANCE[jobId]
            for jobId in self.gainedJobExperience
        )
        win = jobxp + self.gainedKamas
        win -= self.lostPod 
        win -= 20 * investedTime / 7
        jobLvlReward = sum(
            300 * self.gainedJobLevel.get(jobId, 0) * self.JOB_IMPORTANCE[jobId]
            for jobId in self.gainedJobExperience
        )
        win += jobLvlReward
        
        Logger().debug(f"Gained kamas : {self.gainedKamas}")
        Logger().debug(f"Gained %xp : {jobxp}%")
        Logger().debug(f"invested time : {investedTime}")
        Logger().debug(f"lost pod : {self.lostPod}")
        Logger().debug(f"Job lvl reward : {jobLvlReward}")
        Logger().debug(f"total reward : {win}")
        
        if win < -1000000:
            raise Exception("Something is wrong, can't have a reward lesser than -1M")
        return win

    def onNextVertex(self, code, error):
        if error:
            Logger().warning(error)
            if code == MovementFailError.PLAYER_IS_DEAD:
                return self.autoRevive(self.onRevived)
            elif code in [AutoTrip.NO_PATH_FOUND, UseSkill.USE_ERROR, ChangeMap.NEED_QUEST]:
                Logger().warning("Farmer found forbiden resource")
                self.forbidenActions.add(self.lastActionElem)
                return self.makeAction()
            elif code != ChangeMap.LANDED_ON_WRONG_MAP:
                return self.send(
                    KernelEvent.ClientReconnect,
                    f"Error while moving to next step: {error}.",
                )
        reward = 0
        self.currentVertex = self.path.currentVertex
        if self.currentVertex in self.nbrVertexVisites:
            self.nbrVertexVisites[self.currentVertex] += 1
        else:
            self.nbrVertexVisites[self.currentVertex] = 1
            reward += 20000
        timeSinceLastVisit = self.getVertexTimeSinceLastVisit(self.currentVertex)
        self.explorationPercentages.append(
            100.0 * len(self.nbrVertexVisites) / len(self.path.verticies)
        )
        s = time.time()
        next_state = self.getCurrentState()
        if next_state.vertex not in self.areaScrapping:
            self.areaScrapping[next_state.vertex] = {
                "resources": next_state.resources,
                "edges": next_state.outgoingEdges
            }
            with open(self.areaScrappingFile, 'wb') as fp:
                pickle.dump(self.areaScrapping, fp)
        Logger().debug(f"Get state took : {time.time() - s}")
        investedTime = time.time() - self.actionStartTime
        self.timeSpentChangingMap += investedTime
        reward -= 20 * investedTime / 6
        if len(next_state.resources) == 0 and len(next_state.outgoingEdges) == 1:
            Logger().warning("Farmer found dead end")
            self.forbidenActions.add(self.lastActionElem)
        else:
            for r in next_state.resources:
                if r.uid not in self.discovered:
                    self.discovered[r.uid] = next_state.vertex
                    reward += 1000 * self.JOB_IMPORTANCE.get(r.jobId, 10)
        if not next_state.getFarmableResources() and timeSinceLastVisit != -1 and timeSinceLastVisit < 3:
            reward -= 15000
        self.rewards.append(reward)
        self.agent.remember(
            self.lastState.represent(),
            self.lastActionIndex,
            reward,
            next_state.represent(),
        )
        Logger().info(f"Agent got reward : {reward}")
        t = time.time()
        self.agent._train_single(self.lastState.represent(), self.lastActionIndex, reward, next_state.represent())
        if len(self.agent.memory) > 32:
            self.agent.replay(32)
        self.timeSpentLearning += time.time() - t
        self.saveAgentState()
        # if self.lastTimeSentToRandVertex is None or (time.time() - self.lastTimeSentToRandVertex) // 60 > 15:
        #     self.lastTimeSentToRandVertex = time.time()
        #     rv = random.choice(list(self.path.verticies))
        #     self.autotripUseZaap(rv.mapId, rv.zoneId, callback=self.main)
        #     return
        self.lastTimeVertexVisited[self.currentVertex] = time.time()
        self.main()

    def executeAction(self, elem):
        self.gainedKamas = 0
        self.gainedJobExperience = {}
        self.gainedJobLevel = {}
        self.lostPod = 0
        self.actionStartTime = time.time()
        if elem is None:
            raise Exception("Farmer chose a non existing action!")
        if isinstance(elem, CollectableResource):
            if elem in self.forbidenActions or not elem.canFarm(self.jobFilter):
                raise Exception("Farmer chose a disabled resource!")
            elem.farm(self.onResourceCollectEnd, self)
        elif isinstance(elem, Edge):
            Logger().debug("Change map action")
            self.autoTrip(elem.dst.mapId, elem.dst.zoneId, callback=self.onNextVertex)
        else:
            raise TypeError(f"Invalid action type : {type(elem).__name__}")

    def onResourceCollectEnd(self, code, error):
        if not self.running.is_set():
            return
        if error:
            if code in [
                UseSkill.ELEM_BEING_USED,
                UseSkill.ELEM_TAKEN,
                UseSkill.CANT_USE,
                UseSkill.USE_ERROR,
                UseSkill.NO_ENABLED_SKILLS,
                UseSkill.ELEM_UPDATE_TIMEOUT,
                MovementFailError.MOVE_REQUEST_REJECTED,
            ]:
                Logger().error(error)
                self.forbidenActions.add(self.lastActionElem.uid)
                return self.requestMapData(callback=self.main)
            return self.send(KernelEvent.ClientShutdown, error)
        reward = self.getCollecteReward()
        self.rewards.append(reward)
        self.collected.add(self.lastActionElem.uid)
        self.lastTimeResourceCollected[self.lastActionElem.uid] = time.time()
        next_state = self.getCurrentState()
        Logger().info(f"Agent got reward : {reward}")
        t = time.time()
        self.agent._train_single(self.lastState.represent(), self.lastActionIndex, reward, next_state.represent())
        self.timeSpentLearning += time.time() - t
        self.agent.remember(
            self.lastState.represent(),
            self.lastActionIndex,
            reward,
            next_state.represent(),
        )
        BenchmarkTimer(0.55, self.main).start()

    def onInventoryWeightUpdate(self, event, lastWeight, weight, weightMax):
        self.lostPod += weight - lastWeight

    def getCurrentState(self):
        self.currentVertex = self.path.currentVertex
        self.availableResources = self.getAvailableResources()
        self.outgoingEdges = list(self.path.outgoingEdges())
        state = ResourceFarmerState(
            self.currentVertex,
            self.availableResources,
            self.outgoingEdges,
            self.lastTimeVertexVisited,
            self.lastTimeResourceCollected,
            self.nbrVertexVisites,
            self.jobFilter,
            self.JOB_IMPORTANCE,
            self.forbidenActions,
        )
        state.represent()
        return state

    def makeAction(self):
        self.lastState = self.getCurrentState()
        self.updateRespawnTimers(self.lastState.resources)
        self.logActionsTable(self.lastState.resources, self.lastState.outgoingEdges)
        for idx, r in enumerate(self.lastState.resources):
            if idx > ResourceFarmerState.MAX_RESOURCES:
                break
            if r not in self.forbidenActions and r.canFarm():
                if r in self.nonFarmable:
                    self.nonFarmable.remove(r)
            elif r not in self.nonFarmable:
                self.agent.remember(
                    self.lastState.represent(),
                    idx,
                    -90,
                    self.lastState.represent()
                )
                self.nonFarmable.add(r)
        self.lastActionIndex = self.agent.act(self.lastState)
        self.lastActionElem = self.lastState.getAction(self.lastActionIndex)
        self.executeAction(self.lastActionElem)

    def updateRespawnTimers(self, resources: list[CollectableResource]):
        for elem in resources:
            if elem.canCollecte:
                if elem.uid in self.collected:
                    self.collected.remove(elem.uid)
                    if elem.uid in self.lastTimeResourceCollected:
                        respawnTimeEstimate = (
                            time.time() - self.lastTimeResourceCollected[elem.uid]
                        )
                        if elem.resourceId not in self.respawnTimeRecords:
                            self.respawnTimeRecords[elem.resourceId] = []
                        self.respawnTimeRecords[elem.resourceId].append(
                            respawnTimeEstimate
                        )

    def saveAgentState(self):
        agent_state = {
            "agent": {
                "learning_rate": self.agent.learning_rate,
                "gamma": self.agent.gamma,
                "epsilon": self.agent.epsilon,
                "epsilonMin": self.agent.epsilon_min,
                "epsilonDecayRate": self.agent.epsilon_decay            
            },
            "self": {
                "rewards": self.rewards,
                "explorationPercentages": self.explorationPercentages,
                "currentVertex": self.currentVertex,
                "nbrVertexVisites": self.nbrVertexVisites,
                "lastTimeVertexVisited": self.lastTimeVertexVisited,
                "lastTimeResourceCollected": self.lastTimeResourceCollected,
                "forbidenActions": self.forbidenActions,
                "respawnTimeRecords": self.respawnTimeRecords,
                "collected": self.collected,
                "discovered": self.discovered,
                "nonFarmable": self.nonFarmable,
                "timeFarmerStarted": self.timeFarmerStarted,
                "timeSpentChangingMap": self.timeSpentChangingMap,
                "timeSpentFarming": self.timeSpentFarming
            },
        }
        with open(self.stateFile, "wb") as f:
            try:
                pickle.dump(agent_state, f)
            except MemoryError:
                self.rewards.clear()
                self.explorationPercentages.clear()
                pickle.dump(agent_state, f)
        self.agent.save(self.modelFile)

    def loadAgentState(self):
        if os.path.exists(self.stateFile):
            with open(self.stateFile, "rb") as f:
                try:
                    agent_state = pickle.load(f)
                    self.__dict__.update(agent_state["self"])
                    self.agent.__dict__.update(agent_state["agent"])
                except EOFError:
                    pass
        if os.path.exists(self.modelFile):
            self.agent.load(self.modelFile)

    def getVertexTimeSinceLastVisit(self, vertex):
        if vertex in self.lastTimeVertexVisited:
            timeSinceLastVisite = (
                time.time() - self.lastTimeVertexVisited[vertex]
            ) // 60
        else:
            timeSinceLastVisite = -1
        return timeSinceLastVisite
    
    def logActionsTable(self, resources: list[CollectableResource], edges: list[Edge]):
        if resources:
            headers = [
                "jobName",
                "resourceName",
                "enabled",
                "reachable",
                "canFarm",
                "timeSinceLastVisit",
                "respawnTime",
            ]
            summaryTable = PrettyTable(headers)
            for e in resources:
                ertr = self.respawnTimeRecords.get(e.resourceId, None)
                if ertr is not None:
                    ert = sum(ertr) / len(ertr)
                    ert = f"{ert:.2f}"
                else:
                    ert = "unknown"
                if e.uid in self.lastTimeResourceCollected:
                    timeSinceLastCollect = (
                        time.time() - self.lastTimeResourceCollected[e.uid]
                    ) // 60
                else:
                    timeSinceLastCollect = "unknown"
                summaryTable.add_row(
                    [
                        e.resource.skill.parentJob.name,
                        e.resource.skill.gatheredRessource.name,
                        e.resource.enabled,
                        e.reachable,
                        e.canFarm(self.jobFilter),
                        timeSinceLastCollect,
                        ert,
                    ]
                )
            Logger().debug(f"Available resources :\n{summaryTable}")
        if edges:
            headers = ["src", "dst", "timeSinceLastVisit", "nbrVisites"]
            summaryTable = PrettyTable(headers)
            for e in edges:
                if e.dst in self.lastTimeVertexVisited:
                    timeSinceLastCollect = (
                        time.time() - self.lastTimeVertexVisited[e.dst]
                    ) // 60
                else:
                    timeSinceLastCollect = "unknown"
                summaryTable.add_row(
                    [
                        e.src.mapId,
                        e.dst.mapId,
                        timeSinceLastCollect,
                        self.nbrVertexVisites.get(e.dst, 0),
                    ]
                )
            Logger().debug(f"Available edges :\n{summaryTable}")
