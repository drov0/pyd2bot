import collections
import os
import pickle
import random
import time
from typing import cast

import numpy as np
from prettytable import PrettyTable

from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.AbstractFarmBehavior import AbstractFarmBehavior
from pyd2bot.logic.roleplay.behaviors.farm.CollectableResource import (
    CollectableResource,
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


class QResourceFarm(AbstractFarmBehavior):
    EXP_WEIGHT = 0.5
    KAMAS_WEIGHT = 0.5
    JOB_WEIGHTS = {
        36: 10,  # fisher
        2: 100,  # woodshoper,
        26: 10,  # alchimist
        28: 5,  # farmer
        24: 1000,  # miner
    }

    def __init__(
        self,
        timeout=None,
        alpha=0.5,
        gamma=0.9,
        epsilon=0.9999999999999999999999999,
        epsilonMin=0.01,
        epsDecayRate=0.909999999999999999995,
    ):
        super().__init__(timeout)
        self.alpha = alpha  # learning rate
        self.gamma = gamma  # discount factor
        self.epsilon = epsilon  # exploration rate
        self.epsilonMin = epsilonMin
        self.epsilonDecayRate = epsDecayRate
        self.Q = collections.defaultdict(int)
        self.rewards = []
        self.explorationPercentages = []
        self.currentVertex = None
        self.stateFile = os.path.join(CURR_DIR, f"{Logger().prefix}_agent_state.pkl")
        self.jobFilter = BotConfig().jobFilter
        self.path: RandomAreaFarmPath = BotConfig().path
        self.forbidenActions = set()
        self.availableResources = None
        self.outgoingEdges = None
        self.tabuList = {}
        self.lastTimeActionVisited = {}
        self.estimatedResourceRespawnTimes = {}
        self.collected = set()
        self.nonFarmableUpdated = set()
        self.loadAgentState()
        self.explorationPercentages = []
        self.rewards = []

        Logger().debug(f"Qresource farm initialized")
        
    def init(self):
        return True

    def updateEps(self):
        self.epsilon = max(self.epsilon * self.epsilonDecayRate, self.epsilonMin)

    def onObjectAdded(self, event, iw: ItemWrapper):
        if "sac de " in iw.name.lower():
            return Kernel().inventoryManagementFrame.useItem(iw)

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

    def getActionKey(self, elem):
        if isinstance(elem, CollectableResource):
            return elem.resource.id
        elif isinstance(elem, Edge):
            return elem
        raise TypeError(f"Invalid action type : {type(elem).__name__}")

    def executeAction(self, elem):
        self.gainedKamas = 0
        self.gainedJobExperience = {}
        self.lostPod = 0
        self.actionStartTime = time.time()
        if isinstance(elem, CollectableResource):
            if not elem.canFarm(self.jobFilter):
                self.updateQ(-250)
                return self.makeAction()
            elem.farm(self.onResourceCollectEnd, self)
        elif isinstance(elem, Edge):
            Logger().debug("Change map action")
            if elem in self.tabuList:
                self.tabuList[elem] += 1
            else:
                self.tabuList[elem] = 1
            self.autoTrip(elem.dst.mapId, elem.dst.zoneId, callback=self.onNextVertex)
        else:
            raise TypeError(f"Invalid action type : {type(elem).__name__}")

    def onNextVertex(self, code, error):
        if error:
            Logger().warning(error)
            if code == MovementFailError.PLAYER_IS_DEAD:
                return self.autoRevive(self.onRevived)
            elif code in [AutoTrip.NO_PATH_FOUND, UseSkill.USE_ERROR]:
                self.forbidenActions.add(self.lastActionElem)
                return self.makeAction()
            elif code != ChangeMap.LANDED_ON_WRONG_MAP:
                return self.send(
                    KernelEvent.ClientReconnect,
                    f"Error while moving to next step: {error}.",
                )
        self.forbidenActions.clear()
        self.currentVertex = self.path.currentVertex
        self.path.lastVisited[self.currentVertex] = time.time()
        self.lastTimeActionVisited[self.getActionKey(self.lastActionElem)] = time.time()
        self.explorationPercentages.append(self.path.pourcentExplored)
        self.availableResources = self.getAvailableResources()        
        self.outgoingEdges = list(self.path.outgoingEdges())
        reward = 0
        if len(self.availableResources) == 0 and len(self.outgoingEdges) == 1:
            reward = -500
        for r in self.availableResources:
            if r.canCollecte and r.resource.skill.parentJob.id == 24:
                reward += 1000
        self.updateQ(reward)  
        self.updateEps()
        self.saveAgentState()
        self.main()

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
                self.forbidenActions.add(self.lastActionElem.uid)
                return self.requestMapData(callback=self.main)
            return self.send(KernelEvent.ClientShutdown, error)
        reward = self.getCollecteReward()
        self.collected.add(self.getActionKey(self.lastActionElem))
        self.updateQ(reward)        
        self.lastTimeActionVisited[self.getActionKey(self.lastActionElem)] = time.time()
        BenchmarkTimer(0.2, self.main).start()

    def onInventoryWeightUpdate(self, event, lastWeight, weight, weightMax):
        self.lostPod += weight - lastWeight

    def makeAction(self):
        self.availableResources = self.getAvailableResources()        
        self.outgoingEdges = list(self.path.outgoingEdges())
        Logger().debug(f"Bot probability of exploration is : {self.epsilon:.2f}")
        self.logActionsTable(self.availableResources, self.outgoingEdges)
        self.updateRespawnTimers()
        nonForbidenOutgoingEdges = [_ for _ in self.outgoingEdges if self.getActionKey(_) not in self.forbidenActions]
        nonForbidenResources = [_ for _ in self.availableResources if self.getActionKey(_) not in self.forbidenActions]
        actionElements = nonForbidenOutgoingEdges + nonForbidenResources
        actionValues = [
            self.Q.get((self.currentVertex, self.getTimeSinceLastVisit(elem), self.getActionKey(elem)), 0)
            for elem in actionElements
        ]
        softmax_weights = self.softmax(actionValues)
        softmax_explore_weights = self.softmax([-self.tabuList.get(e, 0) for e in nonForbidenOutgoingEdges])
        
        nonFarmable = [r for r in nonForbidenResources if not r.canFarm()]
        farmable = [r for r in nonForbidenResources if r.canFarm()]
        
        for r in farmable:
            if r in self.nonFarmableUpdated:
                self.nonFarmableUpdated.remove(r)
                
        for r in nonFarmable:
            if r not in self.nonFarmableUpdated:
                self.updateQ(0, actionElements, self.currentVertex, self.currentVertex, r)
                self.nonFarmableUpdated.add(r)
                
        if random.random() < 0.9:
            Logger().debug(f"Bot will chose a random action.")
            if farmable:
                actionElem = random.choice(farmable)
            else:
                actionElem = random.choices(nonForbidenOutgoingEdges, weights=softmax_explore_weights, k=1)[0]
        else:
            Logger().debug("Bot will chose the best action.")
            actionElem = random.choices(actionElements, weights=softmax_weights, k=1)[0]

        # Save current state and action for later update
        self.lastVertex = self.currentVertex
        self.lastActionElem = actionElem
        self.executeAction(actionElem)

    def getCollecteReward(self):
        investedTime = time.time() - self.actionStartTime
        jobxp = sum(
            self.gainedJobExperience[jobId] * self.JOB_WEIGHTS[jobId]
            for jobId in self.gainedJobExperience
        )
        win = jobxp * self.EXP_WEIGHT + self.gainedKamas * self.KAMAS_WEIGHT
        if self.lostPod == 0:
            self.lostPod = 1

        cost = investedTime * self.lostPod
        return 900 * win / cost if win != 0 else 0

    def updateQ(self, reward, actionElements=None, vertex=None, lastVertex=None, lastActionElem=None):
        self.rewards.append(reward)
        if actionElements is None:
            actionElements = self.availableResources + self.outgoingEdges
        if vertex is None:
            vertex = self.currentVertex
        if lastVertex is None:
            lastVertex = self.lastVertex
        if lastActionElem is None:
            lastActionElem = self.lastActionElem
        max_q_new_state = max(
            [
                self.Q.get((vertex, self.getTimeSinceLastVisit(elem), self.getActionKey(elem)), 0)
                for elem in actionElements
            ]
        )
        akey = (lastVertex, self.getTimeSinceLastVisit(lastActionElem), self.getActionKey(lastActionElem))
        if akey not in self.Q:
            self.Q[akey] = 0
        self.Q[akey] += self.alpha * (reward + self.gamma * max_q_new_state - self.Q[akey])

    def loadAgentState(self):
        if os.path.exists(self.stateFile):
            with open(self.stateFile, "rb") as f:
                agent_state = pickle.load(f)
            self.path.lastVisited = agent_state["visited"]
            del agent_state["visited"]
            self.__dict__.update(agent_state)

    def saveAgentState(self):
        agent_state = {
            "Q": self.Q,
            "rewards": self.rewards,
            "explorationPercentages": self.explorationPercentages,
            "currentVertex": self.currentVertex,
            "alpha": self.alpha,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
            "epsilonMin": self.epsilonMin,
            "epsilonDecayRate": self.epsilonDecayRate,
            "visited": self.path.lastVisited,
            "tabulist": self.tabuList,
            "estimatedResourceRespawnTimes": self.estimatedResourceRespawnTimes,
            "lastTimeActionVisited": self.lastTimeActionVisited,
            "forbidenActions": self.forbidenActions,
            "nonFarmableUpdated": self.nonFarmableUpdated,
            "collected": self.collected
        }
        with open(self.stateFile, "wb") as f:
            pickle.dump(agent_state, f)
            
    def getTimeSinceLastVisit(self, actionElem):
        last_visit_time = self.lastTimeActionVisited.get(self.getActionKey(actionElem), None)  # assuming you stored the last visit time for each actionElem
        if last_visit_time is None:
            return "unknown"
        elapsed = time.time() - last_visit_time
        elapsed_minutes = elapsed // 60
        if elapsed_minutes < 30:
            return elapsed_minutes
        else:
            return "30+"

    def updateRespawnTimers(self):
        for elem in self.availableResources:
            if elem.canCollecte:
                actionKey = self.getActionKey(elem)
                if actionKey in self.collected:
                    self.collected.remove(actionKey)
                    if actionKey in self.lastTimeActionVisited:
                        respawnTimeEstimate = time.time() - self.lastTimeActionVisited[actionKey]
                        oldEstimate = self.estimatedResourceRespawnTimes.get(
                            elem.resource.skill.gatheredRessource.id, respawnTimeEstimate
                        )
                        newEstimate = (oldEstimate + respawnTimeEstimate) / 2
                        self.estimatedResourceRespawnTimes[elem.resource.skill.gatheredRessource.id] = newEstimate

    # Define a softmax function
    def softmax(self, x):
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum()
    
    def logActionsTable(self, resources: list[CollectableResource], edges: list[Edge]):
        if resources:
            headers = ["jobName", "resourceName", "enabled", "reachable", "canFarm", "timeSinceLastVisit", "respawnTime", "Qvalue"]
            summaryTable = PrettyTable(headers)
            for e in resources:
                akey = (self.currentVertex, self.getTimeSinceLastVisit(e), self.getActionKey(e))
                ert = self.estimatedResourceRespawnTimes.get(e.resource.skill.gatheredRessource.id, "unknown")
                if not isinstance(ert, str):
                    ert = f"{ert:.2f}"
                qv = self.Q.get(akey, 'unknown')
                if not isinstance(qv, str):
                    qv = f"{qv:.2f}"
                summaryTable.add_row(
                    [
                        e.resource.skill.parentJob.name,
                        e.resource.skill.gatheredRessource.name,
                        e.resource.enabled,
                        e.reachable,
                        e.canFarm(self.jobFilter),
                        self.getTimeSinceLastVisit(e),
                        ert,
                        qv
                    ]
                )
            Logger().debug(f"Available resources :\n{summaryTable}")
        if edges:
            headers = ["src", "dst", "lastVisited", "nbrVisites", "Qvalue"]
            summaryTable = PrettyTable(headers)
            for e in edges:
                akey = (self.currentVertex, self.getTimeSinceLastVisit(e), self.getActionKey(e))                
                qv = self.Q.get(akey, 'unknown')
                if not isinstance(qv, str):
                    qv = f"{qv:.2f}"
                summaryTable.add_row(
                    [
                        e.src.mapId,
                        e.dst.mapId,
                        self.getTimeSinceLastVisit(e),
                        self.tabuList.get(e, "unknown"),
                        qv
                    ]
                )
            Logger().debug(f"Available edges :\n{summaryTable}")
            