
import os
from time import perf_counter
from typing import Any, Tuple

from prettytable import PrettyTable

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.farm.CollectableResource import \
    CollectableResource
from pyd2bot.logic.roleplay.behaviors.movement.ChangeMap import ChangeMap
from pyd2bot.models.farmPaths.AbstractFarmPath import AbstractFarmPath
from pyd2bot.models.farmPaths.RandomAreaFarmPath import NoTransitionFound
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.dofus.datacenter.jobs.Job import Job
from pydofus2.com.ankamagames.dofus.datacenter.world.SubArea import SubArea
from pydofus2.com.ankamagames.dofus.internalDatacenter.items.ItemWrapper import \
    ItemWrapper
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.types.MovementFailError import \
    MovementFailError
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Vertex import \
    Vertex
from pydofus2.com.ankamagames.dofus.network.types.game.context.roleplay.job.JobExperience import \
    JobExperience
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

CURR_DIR = os.path.dirname(os.path.abspath(__file__))


class AbstractFarmBehavior(AbstractBehavior):

    path: AbstractFarmPath
    currentTarget: Any = None
    availableResources: list[Any] = None
    def __init__(self, timeout=None):
        self.timeout = timeout
        self.currentVertex: Vertex = None
        super().__init__()

    def run(self, *args, **kwargs):
        self.on(KernelEvent.FightStarted, self.onFight)
        self.on(KernelEvent.PlayerStateChanged, self.onPlayerStateChange)
        self.on(KernelEvent.JobExperienceUpdate, self.onJobExperience)
        self.on(KernelEvent.InventoryWeightUpdate, self.onInventoryWeightUpdate)        
        self.on(KernelEvent.ObtainedItem, self.onObtainedItem)
        self.on(KernelEvent.ObjectAdded, self.onObjectAdded)
        self.inFight = False
        self.init(*args, **kwargs)
        self.main()
    
    def onObjectAdded(self, event, iw: ItemWrapper):
        pass
    
    def updateEps(self):
        self.epsilon = min(self.epsilon * self.epsilonDecayRate, self.epsilonMin)
    
    def onReturnToLastvertex(self, code, err):
        if err:
            return self.finish(code, err)
        Logger().debug(f"Returned to last vertex")
        self.main()
    
    def init(self, *args, **kwargs):
        raise NotImplementedError()

    def onPlayerStateChange(self, event, state, phenixMapId):
        pass

    def onJobExperience(self, event, oldJobXp, jobExperience: JobExperience):
        pass
        
    def onObtainedItem(self, event, iw: ItemWrapper, qty):
        pass
    
    def onInventoryWeightUpdate(self, event):
        pass
    
    def onNextVertex(self, code, error):
        if error:
            if code == MovementFailError.PLAYER_IS_DEAD:
                Logger().warning(f"Player is dead.")
                return self.autoRevive(self.onRevived)
            elif code != ChangeMap.LANDED_ON_WRONG_MAP:
                return self.send(KernelEvent.ClientRestart, "Error while moving to next step: %s." % error)
        self.forbidenActions = set()
        self.main()

    def moveToNextStep(self):
        if not self.running.is_set():
            return
        try:
            self._currEdge = next(self.path)
        except NoTransitionFound as e:
            return self.onBotOutOfFarmPath()
        self.changeMap(edge=self._currEdge, dstMapId=self._currEdge.dst.mapId, callback=self.onNextVertex)

    def onFarmPathMapReached(self, code, error):
        if error:
            return self.send(KernelEvent.ClientRestart, f"Go to path first map failed for reason : {error}")
        self.main()

    def onBotOutOfFarmPath(self):

        self.autotripUseZaap(
            self.path.startVertex.mapId,
            self.path.startVertex.zoneId,
            withSaveZaap=True,
            callback=self.onFarmPathMapReached,
        )

    def onBotUnloaded(self, code, err):
        if err:
            return self.send(KernelEvent.ClientRestart, f"Error while unloading: {err}")
        self.availableResources = None
        self.main()

    def onResourceCollectEnd(self, code, error):
        raise NotImplementedError()

    def onFight(self, event=None):
        Logger().warning(f"Player is in fight")
        self.inFight = True
        self.stopChilds()
        self.once(KernelEvent.RoleplayStarted, self.onRoleplayAfterFight)

    def isCollectErrCodeRequireRefresh(self, code: int) -> bool:
        return False

    def isCollectErrRequireRestart(self, code: int) -> bool:
        return False

    def isCollectErrRequireShutdown(self, code):
        return False

    def collectCurrResource(self):
        raise NotImplementedError()

    def getResourcesTableHeaders(self) -> list[str]:
        raise NotImplementedError()

    def onRevived(self, code, error):
        if error:
            raise Exception(f"[BotWorkflow] Error while autoreviving player: {error}")
        self.availableResources = None
        self.autotripUseZaap(self.currentVertex.mapId, self.currentVertex.zoneId, True, callback=self.main)

    def ongotBackToLastMap(self, code, err):
        if err:
            return self.finish(code, err)
        self.main()

    def onRoleplayAfterFight(self, event=None):
        self.inFight = False
        self.availableResources = None
        self.autotripUseZaap(self.currentVertex.mapId, self.currentVertex.zoneId, callback=self.ongotBackToLastMap)

    def main(self, event=None, error=None):
        if not self.running.is_set():
            return
        if self.timeout and perf_counter() - self.startTime > self.timeout:
            return self.finish(True, None)
        if PlayedCharacterManager().currentMap is None:
            return self.onceMapProcessed(callback=self.main)
        if self.inFight:
            return
        if PlayedCharacterManager().isDead():
            Logger().warning(f"Player is dead.")
            return self.autoRevive(callback=self.onRevived)
        if PlayedCharacterManager().isPodsFull():
            Logger().warning(f"Inventory is almost full will trigger auto unload ...")
            return self.UnloadInBank(callback=self.onBotUnloaded)
        if PlayedCharacterManager().currVertex not in self.path:
            return self.onBotOutOfFarmPath()
        self.makeAction()
    
    def makeAction(self):
        pass
        
    def getAvailableResources(self):
        raise NotImplementedError()
            
    def getAvailableResources(self) -> list[CollectableResource]:
        collectables = Kernel().interactivesFrame.collectables.values()
        collectableResources = [CollectableResource(it) for it in collectables]
        headers = ["jobName", "resourceName", "enabled", "reachable", "canFarm"]
        summaryTable = PrettyTable(headers)
        for e in collectableResources:
            summaryTable.add_row(
                [
                    e.resource.skill.parentJob.name,
                    e.resource.skill.gatheredRessource.name,
                    e.resource.enabled,
                    e.reachable,
                    e.canFarm,
                ]
            )
        if collectableResources:
            Logger().debug(f"Available resources :\n{summaryTable}")
        return collectableResources
