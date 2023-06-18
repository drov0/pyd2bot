from time import perf_counter
from typing import Any, Tuple

from prettytable import PrettyTable

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.bank.UnloadInBank import UnloadInBank
from pyd2bot.logic.roleplay.behaviors.misc.AutoRevive import AutoRevive
from pyd2bot.logic.roleplay.behaviors.movement.AutoTripUseZaap import \
    AutoTripUseZaap
from pyd2bot.logic.roleplay.behaviors.movement.ChangeMap import ChangeMap
from pyd2bot.logic.roleplay.behaviors.movement.GetOutOfAnkarnam import \
    GetOutOfAnkarnam
from pyd2bot.logic.roleplay.behaviors.movement.RequestMapData import \
    RequestMapData
from pyd2bot.models.farmPaths.AbstractFarmPath import AbstractFarmPath
from pyd2bot.models.farmPaths.RandomAreaFarmPath import NoTransitionFound
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.dofus.datacenter.world.SubArea import SubArea
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayInteractivesFrame import \
    InteractiveElementData
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.types.MovementFailError import \
    MovementFailError
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Edge import \
    Edge
from pydofus2.com.ankamagames.jerakine.benchmark.BenchmarkTimer import \
    BenchmarkTimer
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


class AbstractFarmBehavior(AbstractBehavior):
    
    path: AbstractFarmPath
    currentTarget: Any = None
    availableResources: list[Any] = None

    def __init__(self, timeout=None):
        self.timeout = timeout
        super().__init__()

    def run(self, *args, **kwargs):
        self.startTime = perf_counter()
        self.init(*args, **kwargs)
        self.on(KernelEvent.FightStarted, self.onFight)
        self.inFight = False
        self.on(KernelEvent.PlayerStateChanged, self.onPlayerStateChange)
        self.roleplayListener = None
        self._currEdge: Edge = None
        self._currTransition = None
        self.doFarm()

    def init(self, *args, **kwargs):
        raise NotImplementedError()
    
    def onPlayerStateChange(self, event, state, phenixMapId):
        pass

    def onMapChanged(self, code, error):
        if error:            
            if code == MovementFailError.PLAYER_IS_DEAD:
                Logger().warning(f"Player is dead.")
                return AutoRevive().start(callback=self.onRevived, parent=self)
            elif code == MovementFailError.CANT_REACH_DEST_CELL:
                self.path.blackListTransition(self._currTransition, self._currEdge)
                self.moveToNextStep()
            elif code != ChangeMap.LANDED_ON_WRONG_MAP:
                Logger().error(f"Error while moving to next step {error}, code {code}.")
                return self.send(KernelEvent.ClientRestart, "Error while moving to next step: %s." % error)
        self.doFarm()

    def moveToNextStep(self):
        if not self.running.is_set():
            return
        try:
            self._currTransition, self._currEdge = next(self.path)
        except NoTransitionFound as e:
            return self.onBotOutOfFarmPath()
        ChangeMap().start(transition=self._currTransition, dstMapId=self._currEdge.dst.mapId, callback=self.onMapChanged, parent=self)

    def onFarmPathMapReached(self, code, error):
        if error:
            return self.send(KernelEvent.ClientRestart, f"Go to path first map failed for reason : {error}")
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
                    return self.send(KernelEvent.ClientRestart, message=error)
                AutoTripUseZaap().start(
                    self.path.startVertex.mapId, self.path.startVertex.zoneId, callback=self.onFarmPathMapReached, parent=self
                )
            def onGotOutOfAnkarnam(code, error):
                if error:
                    return KernelEventsManager().send(KernelEvent.ClientShutdown, message=error)
                AutoTripUseZaap().start(self.path.startVertex.mapId, self.path.startVertex.zoneId, parent=self.parent, callback=onPosReached)
            return GetOutOfAnkarnam().start(callback=onGotOutOfAnkarnam, parent=self)
        AutoTripUseZaap().start(
            self.path.startVertex.mapId, 
            self.path.startVertex.zoneId,
            withSaveZaap=True,
            callback=self.onFarmPathMapReached, 
            parent=self
        )

    def onBotUnloaded(self, code, err):
        if err:
            return self.send(KernelEvent.ClientRestart, f"Error while unloading: {err}")
        self.availableResources = None
        self.doFarm()
    
    def onCollectEnd(self, code, error):
        if not self.running.is_set():
            return
        if error:
            Logger().warning(error)
            if code == MovementFailError.CANT_REACH_DEST_CELL:
                return self.doFarm()
            if self.isCollectErrCodeRequireRefresh(code):
                return RequestMapData().start(parent=self, callback=self.doFarm)
            elif self.isCollectErrRequireRestart(code):
                return self.send(KernelEvent.ClientRestart, f"Error while farming resource: {error}")
            elif self.isCollectErrRequireShutdown(code):
                return self.send(KernelEvent.ClientShutdown, f"Error while farming resource: {error}")
        BenchmarkTimer(0.1, self.doFarm).start()
    
    def onFight(self, event=None):
        Logger().warning(f"Player is in fight")
        self.inFight = True
        self.stopChilds()
        self.roleplayListener = self.once(KernelEvent.RoleplayStarted, self.onRoleplay)
                
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
        self.doFarm()

    def onRoleplay(self, event=None):
        self.inFight = False
        self.availableResources = None
        KernelEventsManager().onceMapProcessed(self.doFarm, originator=self)

    def doFarm(self, event_id=None, error=None):
        if not self.running.is_set():
            return
        if self.timeout and perf_counter() - self.startTime > self.timeout:
            return self.finish(True, None)
        Logger().info("Do farm called")
        if PlayedCharacterManager().currentMap is None:
            return KernelEventsManager().onceMapProcessed(callback=self.doFarm, originator=self)
        if self.inFight:
            return
        if PlayedCharacterManager().isDead():
            Logger().warning(f"Player is dead.")
            return AutoRevive().start(callback=self.onRevived, parent=self)
        if PlayedCharacterManager().isPodsFull():
            Logger().warning(f"Inventory is almost full will trigger auto unload ...")
            return UnloadInBank().start(callback=self.onBotUnloaded)
        if PlayedCharacterManager().currVertex not in self.path:
            return self.onBotOutOfFarmPath()
        Logger().info("Searching resources to collect ...")
        if self.availableResources is None:
            self.availableResources = self.iterResourceToCollect()
        try:
            self.currentTarget = next(self.availableResources)
        except StopIteration:
            Logger().info("Nothing to farm")
            self.availableResources = None
            return self.moveToNextStep()
        self.collectCurrResource()

    def iterResourceToCollect(self) -> Tuple[InteractiveElementData, int]:
        raise NotImplementedError()

    def getAvailableResourcesTable(self, availableResources) -> str:
        headers = self.getResourcesTableHeaders()
        summaryTable = PrettyTable(headers)
        for e in availableResources:
            summaryTable.add_row([e[k] for k in summaryTable.field_names])
        return summaryTable
