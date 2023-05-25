from typing import Iterable, Tuple

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.MapMove import MapMove
from pyd2bot.logic.roleplay.behaviors.RequestMapData import RequestMapData
from pydofus2.com.ankamagames.berilia.managers.EventsHandler import (Event,
                                                                     Listener)
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayInteractivesFrame import (
    InteractiveElementData, RoleplayInteractivesFrame)
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayWorldFrame import \
    RoleplayWorldFrame
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.types.MovementFailError import \
    MovementFailError
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Edge import \
    Edge
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Transition import \
    Transition
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.TransitionTypeEnum import \
    TransitionTypeEnum
from pydofus2.com.ankamagames.dofus.network.messages.common.basic.BasicPingMessage import \
    BasicPingMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.ChangeMapMessage import \
    ChangeMapMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.interactive.InteractiveUseRequestMessage import \
    InteractiveUseRequestMessage
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.types.positions.MapPoint import MapPoint
from pydofus2.mapTools import MapTools


class ChangeMap(AbstractBehavior):
    MAPCHANGE_TIMEOUT = 15
    REQUEST_MAPDATA_TIMEOUT = 15
    MAX_FAIL_COUNT = 10
    MAX_TIMEOUT_COUNT = 0
    LANDED_ON_WRONG_MAP = 1002
    MAP_ACTION_ALREADY_ONCELL = 1204
    INVALID_TRANSITION = 1342
    MAP_CHANGED_UNEXPECTEDLY = 1556

    def __init__(self) -> None:
        super().__init__()
        self.transition = None
        self.trType = None
        self.mapChangeRequestNbrFails = 0
        self.requestTimeoutCount = 0
        self.mapChangeListener: 'Listener' = None
        self.mapChangeRejectListener: 'Listener' = None
        self.mapChangeIE: InteractiveElementData = None
        self.mapChangeCellId: int = None
        self.iterScrollCells: Iterable[int] = None
        self.currentMPChilds: Iterable[Tuple[int, int]] = None
        self.requestRejectedEvent = None
        self.movementError = None
        self.exactDestination = True
        self.edge = None
        self.mapChangeReqSent = False
        self.forbidenScrollCels = dict[int, list]()

    def run(self, transition: Transition=None, edge: Edge=None, dstMapId=None):
        if transition:
            self.dstMapId = dstMapId
            self.transition = transition
            self.followTransition()
        elif edge:
            self.dstMapId = edge.dst.mapId
            self.edge = edge
            self.followEdge()
        else:
            self.finish(False, "No transition or edge provided")

    @property
    def rpiframe(cls) -> "RoleplayInteractivesFrame":
        return Kernel().worker.getFrameByName("RoleplayInteractivesFrame")
    
    @property
    def worldframe(cls) -> "RoleplayWorldFrame":
        return Kernel().worker.getFrameByName("RoleplayWorldFrame")
    
    @property
    def transitions(self) -> Iterable[Transition]:
        for tr in self.edge.transitions:
            if tr.isValid:
                yield tr

    def followEdge(self):
        try:
            self.transition = next(self.transitions)
        except StopIteration:
            self.finish(self.INVALID_TRANSITION, "No valid transition found!")
        self.followTransition()

    def getTransitionIe(self, transition: Transition, callback) -> "InteractiveElementData":
        if not self.rpiframe:
            return KernelEventsManager().onceFramePushed("RoleplayInteractivesFrame", self.getTransitionIe, [transition], originator=self)
        callback(self.rpiframe.getInteractiveElement(transition.id, transition.skillId))

    def followTransition(self):
        if not self.transition.isValid:
            return self.finish(self.INVALID_TRANSITION, "Trying to follow a non valid transition")
        if self.dstMapId == PlayedCharacterManager().currentMap.mapId:
            return self.finish(True, None)
        self.trType = TransitionTypeEnum(self.transition.type)
        self.askChangeMap()

    def onMapRequestFailed(self, reason: MovementFailError):
        Logger().warning(f"Request failed for reason: {reason.name}")
        self.requestTimeoutCount = 0
        if not self.isScrollTr():
            self.mapChangeRequestNbrFails += 1
            if self.mapChangeRequestNbrFails > self.MAX_FAIL_COUNT:
                if self.edge:
                    self.mapChangeRequestNbrFails = 0
                    return self.followEdge()
                return self.finish(reason, f"Change map failed for reason: {reason.name}")
        else:
            if self.transition.id not in self.forbidenScrollCels:
                self.forbidenScrollCels[self.transition.id] = []
            self.forbidenScrollCels[self.transition.id].append(self.mapChangeCellId)
            self.askChangeMap()
    
    def askChangeMap(self):
        Logger().info(f"{self.trType.name} map change to {self.dstMapId}")
        self.mapChangeReqSent = False
        if self.isInteractiveTr():
            if not self.mapChangeIE:
                def onTransitionIE(ie: InteractiveElementData):
                    if not ie:
                        return self.finish(False, f"InteractiveElement {self.transition.id} not found")
                    self.mapChangeIE = ie
                    iePosition, useInteractive = self.worldframe.getNearestCellToIe(self.mapChangeIE.element, self.mapChangeIE.position)
                    if not useInteractive:
                        return self.finish(False, "Cannot use the interactive")
                    Logger().info(f"Interactive Map change using skill '{ie.skillUID}' on cell '{ie.position.cellId}'.")
                    self.mapChangeCellId = iePosition.cellId
                    self.interactiveMapChange()
                self.getTransitionIe(self.transition, onTransitionIE)
            else:
                self.interactiveMapChange()
        elif self.isScrollTr():
            if not self.iterScrollCells:
                self.iterScrollCells = self.getScrollCells()
            self.scrollMapChange()
        elif self.isMapActionTr():
            self.actionMapChange()
        else:
            self.finish(self.INVALID_TRANSITION, f"Unsupported transition type {self.trType.name}")
    
    def getScrollCells(self):
        if self.transition.id in self.forbidenScrollCels:
            if self.transition.cell not in self.forbidenScrollCels[self.transition.id]:
                yield self.transition.cell
            for c in MapTools.iterMapChangeCells(self.transition.direction):
                if c not in self.forbidenScrollCels[self.transition.id]:
                    yield c
        else:
            yield self.transition.cell
            for c in MapTools.iterMapChangeCells(self.transition.direction):
                yield c

    def onRequestRejectedByServer(self, event: Event, reason: MovementFailError):
        if MapMove().isRunning():
            return Logger().warning(f"Change map timer kicked while map move to cell stil resolving!")
        Logger().warning(f"Movement failed for reason {reason.name}")
        self.mapChangeListener.delete()
        self.mapChangeRejectListener.delete()
        def onResult(code, error):
            if error:
                return self.finish(False, error)
            self.onMapRequestFailed(reason)
        RequestMapData().start(callback=onResult, parent=self)

    def onRequestTimeout(self, listener: Listener):
        if not self.running.is_set():
            Logger().warning("Map change request timeout called while behavior not running!")
            return listener.delete()
        Logger().warning("Map change timeout!")
        if MapMove().isRunning():
            listener.armTimer()
            return Logger().warning(f"Change map timer kicked while map move to cell stil resolving!")
        if not self.isMapActionTr():
            self.requestTimeoutCount += 1
            if self.requestTimeoutCount > self.MAX_TIMEOUT_COUNT:
                listener.delete()
                return self.onMapRequestFailed(MovementFailError.MAPCHANGE_TIMEOUT)
            listener.armTimer()
            self.sendMapChangeRequest()
        else:
            self.onMapRequestFailed(MovementFailError.MAPCHANGE_TIMEOUT)

    def onDestMapProcessedTimeout(self, listene: Listener):
        listene.delete()
        self.finish(False, "Request Map data timeout")
        
    def onCurrentMap(self, event: Event, mapId: int):
        Logger().info("Map changed!")
        if mapId == self.dstMapId:
            if self.mapChangeRejectListener:
                self.mapChangeRejectListener.delete()
            self.mapChangeListener.delete()
            KernelEventsManager().onceMapProcessed(
                lambda: self.finish(True, None),
                mapId=self.dstMapId,
                timeout= 40,
                ontimeout=self.onDestMapProcessedTimeout,
                originator=self
            )
        else:
            self.finish(self.LANDED_ON_WRONG_MAP, f"Landed on new map '{mapId}', different from dest '{self.dstMapId}'.")

    def setupMapChangeListener(self):
        if self.mapChangeListener and not self.mapChangeListener._deleted:
            self.mapChangeListener.delete()
        self.mapChangeListener = KernelEventsManager().on(
            KernelEvent.CURRENT_MAP,
            self.onCurrentMap,
            timeout=self.MAPCHANGE_TIMEOUT,
            ontimeout=self.onRequestTimeout, 
            originator=self
        )
    
    def setupMapChangeRejectListener(self):
        if self.mapChangeRejectListener and not self.mapChangeRejectListener._deleted:
            self.mapChangeRejectListener.delete()
        def onReqReject(event, *args):
            # what about when i receive this when the player confirmed movement but didnt send map request change yet?
            if self.mapChangeReqSent:
                self.onRequestRejectedByServer(event, self.movementError)
        self.mapChangeRejectListener = KernelEventsManager().once(
            self.requestRejectedEvent, 
            onReqReject,
            originator=self
        )
    
    def handleOnsameCellForMapActionCell(self):
        if self.mapChangeListener:
            self.mapChangeListener.delete()
        self.currentMPChilds = MapPoint.fromCellId(self.mapChangeCellId).iterChilds(False)
        try:
            x, y = next(self.currentMPChilds)
        except StopIteration:
            return self.finish(self.MAP_ACTION_ALREADY_ONCELL, "Already on map action cell and can't move away from it.")
        def onMapChangedWhileResolving(event: Event, mapId):
            event.listener.delete()
            self.finish(self.MAP_CHANGED_UNEXPECTEDLY, "Map changed unexpectedly while resolving.")
        def onWaitForMCAfterResolve(listener: Listener):
            listener.delete()
            MapMove().start(self.mapChangeCellId, self.exactDestination, callback=self.onMoveToMapChangeCell, parent=self)
        def onMoved(code, err):
            if err:
                try:    
                    x, y = next(self.currentMPChilds)
                except StopIteration:
                    return self.finish(self.MAP_ACTION_ALREADY_ONCELL, f"Already on map action cell, and can't move away from it for reason : '{err}'.")
                return MapMove().start(MapPoint.fromCoords(x, y).cellId, self.exactDestination, callback=onMoved, parent=self)
            KernelEventsManager().on(
                KernelEvent.CURRENT_MAP, 
                callback=onMapChangedWhileResolving,
                timeout=1,
                ontimeout=onWaitForMCAfterResolve,
                originator=self
            )
        return MapMove().start(MapPoint.fromCoords(x, y).cellId, self.exactDestination, callback=onMoved, parent=self)

    def onMoveToMapChangeCell(self, code, error):
        if error:
            return self.finish(code, error)
        if code == MapMove.ALREADY_ONCELL and self.isMapActionTr():
            return self.handleOnsameCellForMapActionCell()
        Logger().info("Reached map change cell")
        if not self.isMapActionTr():
            self.setupMapChangeListener()
            self.setupMapChangeRejectListener()
            self.sendMapChangeRequest()

    def actionMapChange(self):
        self.requestRejectedEvent = KernelEvent.MOVE_REQUEST_REJECTED
        self.movementError = MovementFailError.MOVE_REQUEST_REJECTED
        self.exactDestination = True
        self.mapChangeCellId = self.transition.cell
        self.setupMapChangeListener()
        MapMove().start(self.mapChangeCellId, self.exactDestination, callback=self.onMoveToMapChangeCell, parent=self)

    def scrollMapChange(self):
        self.requestRejectedEvent = KernelEvent.MOVE_REQUEST_REJECTED
        self.movementError = MovementFailError.MOVE_REQUEST_REJECTED
        self.exactDestination = True
        try:
            self.mapChangeCellId = next(self.iterScrollCells)
        except StopIteration:
            return self.finish(MovementFailError.NOMORE_SCROLL_CELL, f"Tryied all scroll map change cells but no one changed map")
        MapMove().start(self.mapChangeCellId, self.exactDestination, callback=self.onMoveToMapChangeCell, parent=self)       

    def interactiveMapChange(self):
        self.requestRejectedEvent = KernelEvent.INTERACTIVE_USE_ERROR
        self.movementError = MovementFailError.INTERACTIVE_USE_ERROR
        self.exactDestination = False
        MapMove().start(self.mapChangeCellId, self.exactDestination, callback=self.onMoveToMapChangeCell, parent=self)

    def isScrollTr(self):
        return self.trType in [TransitionTypeEnum.SCROLL, TransitionTypeEnum.SCROLL_ACTION]
    
    def isMapActionTr(self):
        return self.trType == TransitionTypeEnum.MAP_ACTION
    
    def isInteractiveTr(self):
        return self.trType == TransitionTypeEnum.INTERACTIVE

    def sendMapChangeRequest(self):
        if self.isInteractiveTr():
            iurmsg = InteractiveUseRequestMessage()
            iurmsg.init(int(self.mapChangeIE.element.elementId), int(self.mapChangeIE.skillUID))
            ConnectionsHandler().send(iurmsg)
        elif self.isScrollTr():
            cmmsg = ChangeMapMessage()
            cmmsg.init(int(self.transition.transitionMapId), False)
            ConnectionsHandler().send(cmmsg)
            self.mapChangeReqSent = True
        else:
            Logger().warning(f"Should not send map change request for trnasition type {self.trType.name}")
