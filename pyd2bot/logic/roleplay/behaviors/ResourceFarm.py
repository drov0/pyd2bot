from enum import Enum
from typing import TYPE_CHECKING, Tuple

from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.AutoTrip import AutoTrip
from pyd2bot.logic.roleplay.behaviors.ChangeMap import ChangeMap
from pyd2bot.logic.roleplay.behaviors.GetOutOfAnkarnam import GetOutOfAnkarnam
from pyd2bot.logic.roleplay.behaviors.RequestMapData import RequestMapData
from pyd2bot.logic.roleplay.behaviors.UseSkill import UseSkill
from pydofus2.com.ankamagames.atouin.managers.MapDisplayManager import \
    MapDisplayManager
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.datacenter.jobs.Job import Job
from pydofus2.com.ankamagames.dofus.datacenter.world.SubArea import SubArea
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.logic.game.common.misc.DofusEntities import \
    DofusEntities
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayInteractivesFrame import \
    InteractiveElementData
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Edge import \
    Edge
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.pathfinding.Pathfinding import \
    Pathfinding

if TYPE_CHECKING:
    from pyd2bot.logic.common.frames.BotWorkflowFrame import BotWorkflowFrame


class FarmerStates(Enum):
    IDLE = 2
    WAITING_FOLLWERS_IDLE = 9
    WAITING_PARTY_MEMBERS_SHOW = 10


class ResourceFarm(AbstractBehavior):
    def __init__(self):
        super().__init__()
        self.state = FarmerStates.IDLE

    def run(self):
        self.jobFilter = BotConfig().jobFilter
        self.path = BotConfig().path
        self.currentCollected = None
        self.doFarm()

    def onMapChanged(self, code, error):
        if error:
            Logger().error("Error while moving to next step: %s" % error)
            return KernelEventsManager().send(KernelEvent.RESTART, "Error while moving to next step: %s" % error)
        self.doFarm()

    def moveToNextStep(self):
        edge: Edge = None
        if not self.running.is_set():
            return
        self._currTransition, edge = next(self.path)
        ChangeMap().start(transition=self._currTransition, dstMapId=edge.dst.mapId, callback=self.onMapChanged, parent=self)

    def onFarmPathMapReached(self, code, error):
        if error:
            return KernelEventsManager().send(KernelEvent.RESTART, f"Go to path first map failed for reason : {error}")
        self.doFarm()

    def onBotOutOfFarmPath(self):
        srcSubArea = SubArea.getSubAreaByMapId(PlayedCharacterManager().currentMap.mapId)
        srcAreaId = srcSubArea._area.id
        dstSubArea = SubArea.getSubAreaByMapId(self.path.startVertex.mapId)
        dstAreaId = dstSubArea._area.id
        if dstAreaId != GetOutOfAnkarnam.ankarnamAreaId and srcAreaId == GetOutOfAnkarnam.ankarnamAreaId:
            Logger().info(f"Auto trip to an Area ({dstSubArea._area.name}) out of {srcSubArea._area.name}.")
            def onPosReached(code, error):
                if error:
                    return KernelEventsManager().send(KernelEvent.SHUTDOWN, message=error)
                AutoTrip().start(
                    self.path.startVertex.mapId, self.path.startVertex.zoneId, callback=self.onFarmPathMapReached, parent=self
                )
            def onGotOutOfAnkarnam(code, error):
                if error:
                    return KernelEventsManager().send(KernelEvent.SHUTDOWN, message=error)
                AutoTrip().start(self.path.startVertex.mapId, self.path.startVertex.zoneId, parent=self.parent, callback=onPosReached)
            return GetOutOfAnkarnam().start(callback=onGotOutOfAnkarnam, parent=self)
        AutoTrip().start(
            self.path.startVertex.mapId, self.path.startVertex.zoneId, callback=self.onFarmPathMapReached, parent=self
        )

    def doFarm(self, event_id=None, error=None):
        Logger().info("do farm called")
        if PlayedCharacterManager().currentMap is None:
            Logger().info("Waiting for map to be processed...")
            return KernelEventsManager().onceMapProcessed(self.doFarm, originator=self)
        if PlayedCharacterManager().currVertex not in self.path:
            Logger().warning("Player out of farm path")
            return self.onBotOutOfFarmPath()
        Logger().info("Searching resources to collect ...")
        availableResources = self.findResourceToCollect()
        availableResources = iter(availableResources)
        def tryNext(code=None, error=None):
            try:
                target = next(availableResources)
            except StopIteration:
                Logger().warning("No resource to farm")
                return self.moveToNextStep()
            self.currentCollected = target["interactiveElement"].element.elementId
            UseSkill().start(ie=target["interactiveElement"], cell=target["nearestCell"], parent=self, callback=onResourceCollectEnd)
        def onResourceCollectEnd(code, error):
            self.currentCollected = None
            if error:
                Logger().warning(error)
                if code == UseSkill.ELEM_BEING_USED:
                    return RequestMapData().start(parent=self, callback=tryNext)
                elif code not in [UseSkill.ELEM_TAKEN, UseSkill.CANT_USE, UseSkill.USE_ERROR]:
                    return KernelEventsManager().send(KernelEvent.RESTART, f"Error while farming resource: {error}")
            if PlayedCharacterManager().inventoryWeightMax > 0 and PlayedCharacterManager().inventoryWeight / PlayedCharacterManager().inventoryWeightMax > 0.95:
                Logger().warning(f"Inventory is almost full will trigger auto unload ...")
                bwf: "BotWorkflowFrame" = Kernel().worker.getFrameByName("BotWorkflowFrame")
                return bwf.unloadInventory(callback=tryNext)
            tryNext()
        tryNext()

    def getInteractive(self, it):
        return Kernel().interactivesFrame.interactives.get(it.id)

    def getDistanceTo(self, mp):
        return PlayedCharacterManager().entity.position.distanceToCell(mp)

    def getPlayerJobLevel(self, jobId) -> int:
        if jobId not in PlayedCharacterManager().jobs:
            if jobId != 1: # base
                job = Job.getJobById(jobId)
                Logger().warn(f"Job '{job.name}' not in player Jobs : {PlayedCharacterManager().jobs}")
            return -1
        return PlayedCharacterManager().jobs[jobId].jobLevel

    def findResourceToCollect(self) -> Tuple[InteractiveElementData, int]:
        collectables = Kernel().interactivesFrame.collectables.values()
        Logger().debug(f"Found {len(collectables)} collectable items : ")
        availableResources = []
        for it in collectables:
            ie = self.getInteractive(it)
            playerJobLevel = self.getPlayerJobLevel(it.skill.parentJobId)
            r = {
                "jobId": it.skill.parentJobId,
                "jobName": it.skill.parentJob.name,
                "resourceId": it.skill.gatheredRessource.id,
                "resourceName": it.skill.gatheredRessource.name,
                "jobLevelMin": it.skill.levelMin,
                "interactiveElement": ie,
                "enabled": it.enabled,
                "playerJobLevel": playerJobLevel,
                "haveTheRequiredJobLevel": playerJobLevel >= it.skill.levelMin,
                "insidePlayerZone": self.insideCurrentPlayerZoneRp(ie.position.cellId),
            }
            playerEntity = DofusEntities().getEntity(PlayedCharacterManager().id)
            movePath = Pathfinding().findPath(playerEntity.position, ie.position)
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
                and r["resourceId"] in self.jobFilter[r["jobId"]]
                and r["haveTheRequiredJobLevel"]
            )
            r["canFarm"] = canFarm
            availableResources.append(r)
        resourceCanCollecte = []
        if availableResources:
            availableResources.sort(key=lambda r : r['distance'])
            Logger().debug(self.getAvailableResourcesTable(availableResources))
            resourceCanCollecte = [r for r in availableResources if r["canFarm"]]
            Logger().debug(f"Can collecte : \n{self.getAvailableResourcesTable(resourceCanCollecte)}")
        else:
            Logger().debug("No available resource to farm")
        return resourceCanCollecte

    def getAvailableResourcesTable(self, availableResources) -> str:
        headers = ["jobName", "resourceName", "distance", "enabled", "reachable", "canFarm"]
        data = [[e[h] for h in headers] for e in availableResources]
        col_widths = [max(len(str(row[i])) for row in data + [headers]) for i in range(len(headers))]
        format_string = "  ".join(["{{:<{}}}".format(width) for width in col_widths])
        tablestr = "\n" + format_string.format(*headers) + "\n"
        tablestr += '-' * (sum(col_widths) + (len(col_widths) - 1) * 2) + "\n"  # Add extra spaces for column separators
        for row in data:
            tablestr += format_string.format(*row) + "\n"
        return tablestr

    def insideCurrentPlayerZoneRp(self, cellId):
        tgtRpZone = MapDisplayManager().dataMap.cells[cellId].linkedZoneRP
        return tgtRpZone == PlayedCharacterManager().currentZoneRp
