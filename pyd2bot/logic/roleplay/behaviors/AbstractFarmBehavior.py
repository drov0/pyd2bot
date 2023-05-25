from typing import Any, Tuple, Type

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.AutoTripUseZaap import AutoTripUseZaap
from pyd2bot.logic.roleplay.behaviors.ChangeMap import ChangeMap
from pyd2bot.logic.roleplay.behaviors.GetOutOfAnkarnam import GetOutOfAnkarnam
from pyd2bot.logic.roleplay.behaviors.RequestMapData import RequestMapData
from pyd2bot.logic.roleplay.behaviors.UnloadInBank import UnloadInBank
from pyd2bot.logic.roleplay.behaviors.UseSkill import UseSkill
from pyd2bot.models.farmPaths.AbstractFarmPath import AbstractFarmPath
from pydofus2.com.ankamagames.atouin.managers.MapDisplayManager import \
    MapDisplayManager
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.datacenter.world.SubArea import SubArea
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayInteractivesFrame import \
    InteractiveElementData
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Edge import \
    Edge
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


class AbstractFarmBehavior(AbstractBehavior):
    
    path: AbstractFarmPath
    currentCollected: Any
    currentTarget: Any
    availableResources: list[Any]
    collectBehavior: AbstractBehavior

    def __init__(self):
        super().__init__()

    def run(self, *args, **kwargs):
        self.init(*args, **kwargs)
        self.doFarm()

    def init(self, *args, **kwargs):
        raise NotImplementedError()
    
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
                AutoTripUseZaap().start(
                    self.path.startVertex.mapId, self.path.startVertex.zoneId, callback=self.onFarmPathMapReached, parent=self
                )
            def onGotOutOfAnkarnam(code, error):
                if error:
                    return KernelEventsManager().send(KernelEvent.SHUTDOWN, message=error)
                AutoTripUseZaap().start(self.path.startVertex.mapId, self.path.startVertex.zoneId, parent=self.parent, callback=onPosReached)
            return GetOutOfAnkarnam().start(callback=onGotOutOfAnkarnam, parent=self)
        AutoTripUseZaap().start(
            self.path.startVertex.mapId, self.path.startVertex.zoneId, callback=self.onFarmPathMapReached, parent=self
        )

    def onBotUnloaded(self, code, err):
        if err:
            return KernelEventsManager().send(KernelEvent.RESTART, f"Error while unloading: {err}")
        self.doFarm()
    
    def onResourceCollectEnd(self, code, error):
        self.currentCollected = None
        if error:
            Logger().warning(error)
            if self.isCollectErrCodeRequireRefresh(code):
                return RequestMapData().start(parent=self, callback=self.collecteNext)
            elif self.isCollectErrRequireRestart(code):
                return KernelEventsManager().send(KernelEvent.RESTART, f"Error while farming resource: {error}")
        self.collecteNext()
    
    def isCollectErrCodeRequireRefresh(self, code: int) -> bool:
        raise NotImplementedError()
    
    def isCollectErrRequireRestart(self, code: int) -> bool:
        raise NotImplementedError()
    
    def getCollectBehaviorArgs(self):
        raise NotImplementedError()
    
    def getCollectBehaviorKwrgs(self):
        raise NotImplementedError()

    def collecteNext(self, code=None, error=None):
        try:
            self.currentTarget = next(self.availableResources)
        except StopIteration:
            Logger().warning("No resource to farm")
            return self.moveToNextStep()
        self.collectBehavior().start(*self.getCollectBehaviorArgs(), **self.getCollectBehaviorKwrgs(), parent=self, callback=self.onResourceCollectEnd)
    
    def isPodsFull(self):
        return PlayedCharacterManager().inventoryWeightMax > 0 and PlayedCharacterManager().inventoryWeight / PlayedCharacterManager().inventoryWeightMax > 0.95
    
    def getResourcesTableHeaders(self) -> list[str]:
        raise NotImplementedError()

    def doFarm(self, event_id=None, error=None):
        Logger().info("Do farm called")
        if PlayedCharacterManager().currentMap is None:
            return KernelEventsManager().onceMapProcessed(self.doFarm, originator=self)
        if PlayedCharacterManager().currVertex not in self.path:
            return self.onBotOutOfFarmPath()
        Logger().info("Searching resources to collect ...")
        if self.isPodsFull():
            Logger().warning(f"Inventory is almost full will trigger auto unload ...")
            return UnloadInBank().start(callback=self.onBotUnloaded)
        availableResources = self.findResourceToCollect()
        self.availableResources = iter(availableResources)
        self.collecteNext()

    def findResourceToCollect(self) -> Tuple[InteractiveElementData, int]:
        raise NotImplementedError()

    def getAvailableResourcesTable(self, availableResources) -> str:
        headers = self.getResourcesTableHeaders()
        data = [[e[h] for h in headers] for e in availableResources]
        col_widths = [max(len(str(row[i])) for row in data + [headers]) for i in range(len(headers))]
        format_string = "  ".join(["{{:<{}}}".format(width) for width in col_widths])
        tablestr = "\n" + format_string.format(*headers) + "\n"
        tablestr += '-' * (sum(col_widths) + (len(col_widths) - 1) * 2) + "\n"  # Add extra spaces for column separators
        for row in data:
            color = '\033[0;31m' if not row[-1] else '\033[0;32m'
            cancelColor = '\033[0m'
            tablestr += color + format_string.format(*row) + cancelColor + "\n"
        return tablestr

    def insideCurrentPlayerZoneRp(self, cellId):
        tgtRpZone = MapDisplayManager().dataMap.cells[cellId].linkedZoneRP
        return tgtRpZone == PlayedCharacterManager().currentZoneRp
