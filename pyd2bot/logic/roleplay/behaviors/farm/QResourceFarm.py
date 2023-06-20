import collections
import math
import os
import pickle
import random
from time import perf_counter
from typing import cast

from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.AbstractFarmBehavior import \
    AbstractFarmBehavior
from pyd2bot.logic.roleplay.behaviors.farm.CollectableResource import \
    CollectableResource
from pyd2bot.logic.roleplay.behaviors.movement.ChangeMap import ChangeMap
from pyd2bot.logic.roleplay.behaviors.skill.UseSkill import UseSkill
from pyd2bot.models.farmPaths.RandomAreaFarmPath import RandomAreaFarmPath
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.dofus.datacenter.jobs.Job import Job
from pydofus2.com.ankamagames.dofus.internalDatacenter.items.ItemWrapper import \
    ItemWrapper
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.types.MovementFailError import \
    MovementFailError
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Edge import \
    Edge
from pydofus2.com.ankamagames.dofus.network.types.game.context.roleplay.job.JobExperience import \
    JobExperience
from pydofus2.com.ankamagames.jerakine.benchmark.BenchmarkTimer import \
    BenchmarkTimer
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
    
    def __init__(self, timeout=None, alpha=0.5, gamma=0.9, epsilon=0.9999, epsilonMin = 0.01, epsDecayRate = 0.995):
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
        self.loadAgentState()
        
    def init(self):   
        if self.currentVertex:
            return self.autotripUseZaap(self.currentVertex.mapId, self.currentVertex.zoneId, True, callback=self.onReturnToLastvertex)
        self.currentVertex = self.path.currentVertex

    def onObjectAdded(self, event, iw: ItemWrapper):
        if "sac de " in iw.name.lower():
            return Kernel().inventoryManagementFrame.useItem(iw.objectGID, iw.quantity, False, iw)
        
    def onJobExperience(self, event, oldJobXp, jobExperience: JobExperience):
        xpPourcent = (
            100
            * (jobExperience.jobXP - oldJobXp)
            / (jobExperience.jobXpNextLevelFloor - jobExperience.jobXpLevelFloor)
        )
        job = Job.getJobById(jobExperience.jobId)
        Logger().debug(f"Job {job.name} gained {xpPourcent:.2f}% experince")
        
        self.gainedJobExperience[jobExperience.jobId] += xpPourcent
        
    def onObtainedItem(self, event, iw: ItemWrapper, qty):
        averageKamasWon = Kernel().averagePricesFrame.getItemAveragePrice(iw.objectGID) * qty
        self.lostPod += iw.realWeight * qty
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
        self.actionStartTime = perf_counter()
        if isinstance(elem, CollectableResource):
            elem.farm(self.onResourceCollectEnd, self)
        elif isinstance(elem, Edge):
            self.autoTrip(elem.dst.mapId, elem.dst.zoneId, callback=self.onNextVertex)
        else:
            raise TypeError(f"Invalid action type : {type(elem).__name__}")

    def onNextVertex(self, code, error):
        if error:
            if code == MovementFailError.PLAYER_IS_DEAD:
                Logger().warning(f"Player is dead.")
                return self.autoRevive(self.onRevived)
            elif code != ChangeMap.LANDED_ON_WRONG_MAP:
                return self.send(KernelEvent.ClientShutdown, "Error while moving to next step: %s." % error)
        self.forbidenActions.clear()
        self.currentVertex = self.path.currentVertex
        if self.currentVertex not in self.path.visited:
            self.path.visited.add(self.currentVertex)
            self.explorationPercentages.append(self.path.pourcentExplored)
            win = 500 * math.exp(-5 * (100 - self.path.pourcentExplored) / 100)
            cost = perf_counter() - self.actionStartTime
            reward = win / cost
            self.updateQ(reward)
            self.updateEps()
        self.saveAgentState()
        self.main()
        
    def onResourceCollectEnd(self, code, error):
        self.lastActionkey = cast(CollectableResource, self.lastActionkey)
        if not self.running.is_set():
            return
        if error:
            if code in [UseSkill.ELEM_BEING_USED, UseSkill.ELEM_TAKEN, UseSkill.CANT_USE, UseSkill.USE_ERROR]:
                self.forbidenActions.add(self.lastActionkey)
                return self.requestMapData(callback=self.main)
            return KernelEventsManager().send(KernelEvent.ClientShutdown, error)
        reward = self.getCollecteReward()
        self.updateQ(reward)
        BenchmarkTimer(0.25, self.main).start()
        
    def makeAction(self):
        self.availableResources = [r for r in self.getAvailableResources() if r.canFarm]
        self.outgoingEdges = list(self.path.outgoingEdges())
        actionElements = [item for item in self.outgoingEdges + self.availableResources if self.getActionKey(item) not in self.forbidenActions]
        # Select action using epsilon-greedy policy
        if random.random() < self.epsilon:
            actionElem = random.choice(actionElements)
        else:
            actionElem = max(actionElements, key=lambda elem: self.Q[(self.currentVertex, self.getActionKey(elem))])
        # Save current state and action for later update
        self.lastVertex = self.currentVertex
        self.lastActionkey = self.getActionKey(actionElem)
        self.executeAction(actionElem)
        
    def getCollecteReward(self):
        investedTime = (perf_counter() - self.actionStartTime)
        jobxp = sum(self.gainedJobExperience[jobId] * self.JOB_WEIGHTS[jobId] for jobId in self.gainedJobExperience)
        win = jobxp * self.EXP_WEIGHT + self.gainedKamas * self.KAMAS_WEIGHT
        cost =  investedTime * self.lostPod
        return win / cost if win != 0 else 0
    
    def updateQ(self, reward):
        self.rewards.append(reward)
        actionElements = self.outgoingEdges + self.availableResources
        max_q_new_state = max([self.Q[(self.currentVertex, self.getActionKey(elem))] for elem in actionElements])
        self.Q[(self.lastVertex, self.lastActionkey)] += self.alpha * (
            reward + self.gamma * max_q_new_state - self.Q[(self.lastVertex, self.lastActionkey)]
        )

    def loadAgentState(self):
        if os.path.exists(self.stateFile):
            with open(self.stateFile, 'rb') as f:
                agent_state = pickle.load(f)
            self.path.visited = agent_state['visited']
            del agent_state['visited']
            self.__dict__.update(agent_state)

    def saveAgentState(self):
        agent_state = {
            'Q': self.Q,
            'rewards': self.rewards,
            'explorationPercentages': self.explorationPercentages,
            "currentVertex": self.currentVertex,
            'alpha': self.alpha,
            'gamma': self.gamma,
            'epsilon': self.epsilon,
            'epsilonMin': self.epsilonMin,
            'epsilonDecayRate': self.epsilonDecayRate,
            'visited': self.path.visited
        }
        with open(self.stateFile, 'wb') as f:
            pickle.dump(agent_state, f)