from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.AbstractFarmBehavior import \
    AbstractFarmBehavior
from pyd2bot.logic.roleplay.behaviors.skill.UseSkill import UseSkill
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.dofus.internalDatacenter.DataEnum import DataEnum
from pydofus2.com.ankamagames.dofus.internalDatacenter.items.ItemWrapper import \
    ItemWrapper
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.pathfinding.Pathfinding import \
    Pathfinding


class ResourceFarm(AbstractFarmBehavior):
    
    def __init__(self, timeout=None):
        super().__init__(timeout)
        
    def init(self):
        self.jobFilter = BotConfig().jobFilter
        self.path = BotConfig().path
        self.send(KernelEvent.ObjectAdded, self.onObjectAdded)

    def onObjectAdded(self, event, iw:ItemWrapper):
        Logger().debug(f"Received item : {iw.name} x {iw.quantity}")
        if "sac de " in iw.name.lower():
            return Kernel().inventoryManagementFrame.useItem(iw.objectUID, iw.quantity, False, iw)
        
    def isCollectErrRequireRestart(self, code: int) -> bool:
        return code not in [UseSkill.ELEM_BEING_USED, UseSkill.ELEM_TAKEN, UseSkill.CANT_USE, UseSkill.USE_ERROR]
    
    def isCollectErrCodeRequireRefresh(self, code: int) -> bool:
        return code in [UseSkill.ELEM_BEING_USED]
    
    def isCollectErrRequireShutdown(self, code):
        return False
    
    def collectCurrResource(self):
        self.useSkill(ie=self.currentTarget["interactiveElement"], cell=self.currentTarget["nearestCell"], callback=self.onCollectEnd)

    def getResourcesTableHeaders(self) -> list[str]:
        return ["jobName", "resourceName", "distance", "enabled", "reachable", "canFarm"]

    def iterResourceToCollect(self) -> list[dict]:
        collectables = Kernel().interactivesFrame.collectables.values()
        availableResources = []
        for it in collectables:
            ie = Kernel().interactivesFrame.interactives.get(it.id)
            playerJobLevel = PlayedCharacterManager().joblevel(it.skill.parentJobId)
            r = {
                "jobId": it.skill.parentJobId,
                "jobName": it.skill.parentJob.name,
                "resourceId": it.skill.gatheredRessource.id,
                "resourceName": it.skill.gatheredRessource.name,
                "jobLevelMin": it.skill.levelMin,
                "interactiveElement": ie,
                "enabled": it.enabled,
                "playerJobLevel": playerJobLevel,
                "hasLevel": playerJobLevel >= it.skill.levelMin,
                "insidePlayerZone": PlayedCharacterManager().inSameRpZone(ie.position.cellId),
            }
            movePath = Pathfinding().findPath(PlayedCharacterManager().entity.position, ie.position)
            r["reachable"] = movePath is not None and movePath.end.distanceTo(ie.position) <= it.skill.range
            if movePath:
                r["nearestCell"] = movePath.end.cellId
                r["distance"] = len(movePath)
            else:
                r["nearestCell"] = None
                r["distance"] = float("inf")
            canFarm = (
                r["reachable"]
                and r["enabled"]
                and r["jobId"] in self.jobFilter
                and (not self.jobFilter[r["jobId"]] or r["resourceId"] in self.jobFilter[r["jobId"]])
                and r["hasLevel"]
            )
            r["canFarm"] = canFarm
            availableResources.append(r)
        if availableResources:
            Logger().debug(f"Available resources :\n{self.getAvailableResourcesTable(availableResources)}")
            availableResources.sort(key=lambda r : r['distance'])
            for r in availableResources:
                if r['canFarm'] :
                    yield r
        else:
            return []

