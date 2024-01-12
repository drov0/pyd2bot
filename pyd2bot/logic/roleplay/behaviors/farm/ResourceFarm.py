from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.AbstractFarmBehavior import \
    AbstractFarmBehavior
from pyd2bot.logic.roleplay.behaviors.farm.CollectableResource import \
    CollectableResource
from pyd2bot.logic.roleplay.behaviors.skill.UseSkill import UseSkill
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.dofus.internalDatacenter.items.ItemWrapper import \
    ItemWrapper
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.types.MovementFailError import \
    MovementFailError
from pydofus2.com.ankamagames.jerakine.benchmark.BenchmarkTimer import \
    BenchmarkTimer
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from prettytable import PrettyTable


class ResourceFarm(AbstractFarmBehavior):
    
    def __init__(self, timeout=None):
        super().__init__(timeout)

    def init(self):
        self.jobFilter = BotConfig().jobFilter
        self.path = BotConfig().path
        self.currentTarget: CollectableResource = None
        self.on(KernelEvent.ObjectAdded, self.onObjectAdded)
        self.on(KernelEvent.ObtainedItem, self.onObtainedItem)

    def makeAction(self):
        '''
        This function is called when the bot is ready to make an action. 
        It will select the next resource to farm and move to it.
        '''
        available_resources = self.getAvailableResources()
        farmable_resources = [r for r in available_resources if r.canFarm(self.jobFilter)]
        nonForbidenResources = [r for r in farmable_resources if r.uid not in self.forbidenActions]
        nonForbidenResources.sort(key=lambda r: r.distance)
        if len(nonForbidenResources) == 0:
            Logger().warning("No farmable resource found!")
            self.moveToNextStep()
        else:
            self.logResourcesTable(nonForbidenResources)
            self.currentTarget = nonForbidenResources[0]
            self.useSkill(
                elementId=self.currentTarget.resource.id,
                skilluid=self.currentTarget.resource.interactiveSkill.skillInstanceUid,
                cell=self.currentTarget.nearestCell.cellId,
                callback=self.onResourceCollectEnd
            )
        
    def onObtainedItem(self, event, iw: ItemWrapper, qty):
        averageKamasWon = (
            Kernel().averagePricesFrame.getItemAveragePrice(iw.objectGID) * qty
        )
        Logger().debug(f"Average kamas won: {averageKamasWon}")

    def onResourceCollectEnd(self, code, error, iePosition=None):
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
                Logger().warning(f"Error while collecting resource: {error}, not a fatal error, restarting.")
                self.forbidenActions.add(self.currentTarget.uid)
                return self.requestMapData(callback=self.main)
            return self.send(KernelEvent.ClientShutdown, message=error)
        BenchmarkTimer(0.2, self.main).start()
        
    def getAvailableResources(self) -> list[CollectableResource]:
        if not Kernel().interactivesFrame:
            Logger().error("No interactives frame found")
            return None
        collectables = Kernel().interactivesFrame.collectables.values()
        collectableResources = [CollectableResource(it) for it in collectables]
        return collectableResources

    def logResourcesTable(self, resources: list[CollectableResource]):
        if resources:
            headers = ["jobName", "resourceName", "enabled", "reachable", "canFarm", ]
            summaryTable = PrettyTable(headers)
            for e in resources:
                summaryTable.add_row(
                    [
                        e.resource.skill.parentJob.name,
                        e.resource.skill.gatheredRessource.name,
                        e.resource.enabled,
                        e.reachable,
                        e.canFarm(self.jobFilter)
                    ]
                )
            Logger().debug(f"Available resources :\n{summaryTable}")
