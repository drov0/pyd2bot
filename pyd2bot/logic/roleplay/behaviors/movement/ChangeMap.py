from typing import Iterable, Tuple

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.movement.MapMove import MapMove
from pyd2bot.logic.roleplay.behaviors.movement.RequestMapData import \
    RequestMapData
from pyd2bot.logic.roleplay.behaviors.skill.UseSkill import UseSkill
from pydofus2.com.ankamagames.berilia.managers.EventsHandler import (Event,
                                                                     Listener)
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.dofus.datacenter.interactives.Interactive import Interactive
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.InteractiveElementData import InteractiveElementData
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.types.MovementFailError import \
    MovementFailError
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Edge import \
    Edge
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Transition import \
    Transition
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.TransitionTypeEnum import \
    TransitionTypeEnum
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.ChangeMapMessage import \
    ChangeMapMessage
from pydofus2.com.ankamagames.jerakine.benchmark.BenchmarkTimer import \
    BenchmarkTimer
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.types.positions.MapPoint import MapPoint
from pydofus2.mapTools import MapTools


class ChangeMap(AbstractBehavior):
    MAPCHANGE_TIMEOUT = 20
    REQUEST_MAPDATA_TIMEOUT = 15
    MAX_FAIL_COUNT = 10
    MAX_TIMEOUT_COUNT = 0
    LANDED_ON_WRONG_MAP = 1002
    MAP_ACTION_ALREADY_ONCELL = 1204
    INVALID_TRANSITION = 1342
    MAP_CHANGED_UNEXPECTEDLY = 1556
    NEED_QUEST = 879908

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
        self.forbidenScrollCells = dict[int, list]()
        self._transitions = None
        self._scrollMapChangeRequestTimer: BenchmarkTimer = None

    def run(self, transition: Transition=None, edge: Edge=None, dstMapId=None):
        self.on(KernelEvent.ServerTextInfo, self.onServerTextInfo)
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
            
    def onServerTextInfo(self, event, msgId, msgType, textId, text, params):
        if textId == 4908:
            Logger().error("Need a quest to be completed")
            return self.finish(self.NEED_QUEST, "Need a quest to be completed")

    @property
    def transitions(self):
        if not self._transitions:
            self._transitions = self.transitionsGen()
        return self._transitions
    
    def transitionsGen(self) -> Iterable[Transition]:
        mapAction_trs = []
        scroll_trs = []
        other_trs = []
        for tr in self.edge.transitions:
            if tr.isValid:
                if TransitionTypeEnum(tr.type) == TransitionTypeEnum.MAP_ACTION:
                    mapAction_trs.append(tr)
                elif TransitionTypeEnum(tr.type) in [TransitionTypeEnum.SCROLL, TransitionTypeEnum.SCROLL_ACTION]:
                    scroll_trs.append(tr)
                else:
                    other_trs.append(tr)
        all_trs = mapAction_trs + scroll_trs + other_trs
        return iter(all_trs)

    def followEdge(self):
        try:
            self.transition: Transition = next(self.transitions)
            self.trType = TransitionTypeEnum(self.transition.type)
            if self.isInteractiveTr():
                self.mapChangeIE = Kernel().interactivesFrame._ie.get(self.transition.id)
                if self.mapChangeIE:
                    trie = Interactive.getInteractiveById(self.mapChangeIE.element.elementTypeId)
                    if trie:
                        Logger().debug(f"Transition IE is {trie.name} ==> {trie.actionId}")
                    if self.mapChangeIE.element.elementTypeId == Kernel().interactivesFrame.ZAAP_TYPEID:
                        Logger().warning(f"Current transition is using a Zaap it must be discarded.")
                        self.transition = next(self.transitions)
                else:
                    Logger().error(f"Unable to find transiton IE {self.transition.id}!. {Kernel().interactivesFrame._ie}")
                    self.transition = next(self.transitions)
        except StopIteration:
            return self.finish(self.INVALID_TRANSITION, "No valid transition found!, available transitions: " + str(self.edge.transitions))
        self.followTransition()

    def getTransitionIe(self, transition: Transition, callback) -> "InteractiveElementData":
        if not self.rpiframe:
            return self.onceFramePushed("RoleplayInteractivesFrame", self.getTransitionIe, [transition])
        callback(self.rpiframe.getInteractiveElement(transition.id, transition.skillId))

    def followTransition(self):
        if not self.transition.isValid:
            return self.finish(self.INVALID_TRANSITION, "Trying to follow a non valid transition")
        if self.dstMapId == PlayedCharacterManager().currentMap.mapId:
            return self.finish(True, None)
        self.trType = TransitionTypeEnum(self.transition.type)
        self.askChangeMap()
    
    def askChangeMap(self):
        Logger().info(f"{self.trType.name} map change to {self.dstMapId}")
        self.mapChangeReqSent = False
        if self.isInteractiveTr():
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
        if self.transition.id in self.forbidenScrollCells:
            if self.transition.cell not in self.forbidenScrollCells[self.transition]:
                yield self.transition.cell
            for c in MapTools.iterMapChangeCells(self.transition.direction):
                if c not in self.forbidenScrollCells[self.transition]:
                    yield c
        else:
            yield self.transition.cell
            for c in MapTools.iterMapChangeCells(self.transition.direction):
                yield c

    def onRequestRejectedByServer(self, event: Event, reason: MovementFailError):
        if MapMove().isRunning():
            return Logger().warning(f"Change map timer kicked while map move to cell stil resolving!")
        Logger().warning(f"Movement failed for reason {reason.name}")
        if self.mapChangeListener:
            self.mapChangeListener.delete()
        if self.mapChangeRejectListener:
            self.mapChangeRejectListener.delete()
        def onResult(code, error):
            if error:
                return self.finish(False, error)
            self.onMapRequestFailed(reason)
        RequestMapData().start(callback=onResult, parent=self)
        
    def onMapRequestFailed(self, reason: MovementFailError):
        Logger().warning(f"Request failed for reason: {reason.name}")
        self.requestTimeoutCount = 0
        if self.isInteractiveTr():
            self.followEdge()
        elif not self.isScrollTr():
            self.mapChangeRequestNbrFails += 1
            if self.mapChangeRequestNbrFails > self.MAX_FAIL_COUNT:
                if self.edge:
                    self.mapChangeRequestNbrFails = 0
                    return self.followEdge()
                return self.finish(reason, f"Change map failed for reason: {reason.name}")
            self.askChangeMap()
        else:
            if self.transition not in self.forbidenScrollCells:
                self.forbidenScrollCells[self.transition] = []
            self.forbidenScrollCells[self.transition].append(self.mapChangeCellId)
            self.askChangeMap()
            
    def onRequestTimeout(self, listener: Listener):
        if not self.running.is_set():
            Logger().warning("Map change request timeout called while behavior not running!")
            return listener.delete()
        Logger().warning("Map change timeout!")
        if MapMove().isRunning():
            listener.armTimer()
            return Logger().warning(f"Change map timer kicked while map move to cell stil resolving!")
        if self.isInteractiveTr():
            self.onMapRequestFailed(MovementFailError.MAPCHANGE_TIMEOUT)
        elif not self.isMapActionTr():
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
        if self.mapChangeRejectListener:
            self.mapChangeRejectListener.delete()
        if self.mapChangeListener:
            self.mapChangeListener.delete()
        if UseSkill().isRunning():
            Logger().warning("Received current map while still using skill")
            UseSkill().stop()
        if self._scrollMapChangeRequestTimer:
            Logger().warning("Received current map while still didn't send map change request")
            self._scrollMapChangeRequestTimer.cancel()
            
        if mapId == self.dstMapId:
            callback = lambda: self.finish(True, None)
        else:
            callback = lambda: self.finish(self.LANDED_ON_WRONG_MAP, f"Landed on new map '{mapId}', different from dest '{self.dstMapId}'.")
        self.onceMapProcessed(
            callback=callback,
            mapId=mapId,
            timeout=20,
            ontimeout=self.onDestMapProcessedTimeout
        )

    def setupMapChangeListener(self):
        if self.mapChangeListener:
            self.mapChangeListener.delete()
        self.mapChangeListener = self.on(
            KernelEvent.CurrentMap,
            self.onCurrentMap,
            timeout=self.MAPCHANGE_TIMEOUT,
            ontimeout=self.onRequestTimeout, 
        )
    
    def setupMapChangeRejectListener(self):
        if self.mapChangeRejectListener:
            self.mapChangeRejectListener.delete()
        def onReqReject(event, *args):
            # what about when i receive this when the player confirmed movement but didn't send map request change yet?
            if self.mapChangeReqSent:
                self.onRequestRejectedByServer(event, self.movementError)
        self.mapChangeRejectListener = self.once(
            self.requestRejectedEvent, 
            onReqReject,
        )
    
    def handleOnsameCellForMapActionCell(self):
        self.currentMPChilds = MapPoint.fromCellId(self.mapChangeCellId).iterChilds(False, True)
        try:
            x, y = next(self.currentMPChilds)
        except StopIteration:
            return self.finish(self.MAP_ACTION_ALREADY_ONCELL, "Already on map action cell and can't move away from it.")
        def onMapChangedWhileResolving(event: Event, mapId):
            event.listener.delete()
            self.finish(self.MAP_CHANGED_UNEXPECTEDLY, "Map changed unexpectedly while resolving.")
        def onWaitForMCAfterResolve(listener: Listener):
            listener.delete()
            self.mapMove(self.mapChangeCellId, self.exactDestination, callback=self.onMoveToMapChangeCell)
        def onMoved(code, err):
            if err:
                try:    
                    x, y = next(self.currentMPChilds)
                except StopIteration:
                    return self.finish(self.MAP_ACTION_ALREADY_ONCELL, f"Already on map action cell, and can't move away from it for reason : '{err}'.")
                return self.mapMove(MapPoint.fromCoords(x, y).cellId, self.exactDestination, callback=onMoved)
            self.on(
                KernelEvent.CurrentMap, 
                callback=onMapChangedWhileResolving,
                timeout=1,
                ontimeout=onWaitForMCAfterResolve,
            )
        return self.mapMove(MapPoint.fromCoords(x, y).cellId, self.exactDestination, callback=onMoved)

    def onMoveToMapChangeCell(self, code, error):
        if code == MapMove.ALREADY_ONCELL and self.isMapActionTr():
            Logger().debug("Already on map action cell, need to move away from it first")
            return self.handleOnsameCellForMapActionCell()
        elif code == MovementFailError.MOVE_REQUEST_REJECTED:
            if self.isScrollTr():
                if self.transition not in self.forbidenScrollCells:
                    self.forbidenScrollCells[self.transition] = []
                self.forbidenScrollCells[self.transition].append(self.mapChangeCellId)
                return self.askChangeMap()
        elif code == MovementFailError.CANT_REACH_DEST_CELL:
            if self.edge:
                return self.followEdge()
        if error:
            return self.finish(code, error)
        Logger().info("Reached map change cell")
        if not self.isMapActionTr():
            self.setupMapChangeRejectListener()
            self._scrollMapChangeRequestTimer = BenchmarkTimer(0.5, self.sendMapChangeRequest).start()

    def actionMapChange(self):
        self.requestRejectedEvent = KernelEvent.MovementRequestRejected
        self.movementError = MovementFailError.MOVE_REQUEST_REJECTED
        self.exactDestination = True
        self.mapChangeCellId = self.transition.cell
        self.setupMapChangeListener()
        self.mapMove(self.mapChangeCellId, self.exactDestination, callback=self.onMoveToMapChangeCell)

    def scrollMapChange(self):
        self.requestRejectedEvent = KernelEvent.MovementRequestRejected
        self.movementError = MovementFailError.MOVE_REQUEST_REJECTED
        self.exactDestination = True
        try:
            self.mapChangeCellId = next(self.iterScrollCells)
        except StopIteration:
            if self.edge:
                return self.followEdge()
            return self.finish(MovementFailError.NOMORE_SCROLL_CELL, f"Tryied all scroll map change cells but no one changed map")
        self.setupMapChangeListener()
        self.mapMove(self.mapChangeCellId, self.exactDestination, forMapChange=True, mapChangeDirection=self.transition.direction, callback=self.onMoveToMapChangeCell)       

    def onChangeMapIE(self, code, err):
        if err:
            if code == UseSkill.USE_ERROR:
                if self.edge:
                    return self.followEdge()
            return self.finish(code, err)
        Logger().debug("Map change IE used")
        self.setupMapChangeRejectListener()
        
    def interactiveMapChange(self):
        self.requestRejectedEvent = KernelEvent.InteractiveUseError
        self.movementError = MovementFailError.INTERACTIVE_USE_ERROR
        self.exactDestination = False
        self.setupMapChangeListener()
        self.useSkill(elementId=self.transition.id, skilluid=self.transition.skillId, cell=self.transition.cell, callback=self.onChangeMapIE)

    def isScrollTr(self):
        return self.trType in [TransitionTypeEnum.SCROLL, TransitionTypeEnum.SCROLL_ACTION]
    
    def isMapActionTr(self):
        return self.trType == TransitionTypeEnum.MAP_ACTION
    
    def isInteractiveTr(self):
        return self.trType == TransitionTypeEnum.INTERACTIVE

    def sendMapChangeRequest(self):
        cmmsg = ChangeMapMessage()
        cmmsg.init(int(self.transition.transitionMapId), False)
        ConnectionsHandler().send(cmmsg)
        self.mapChangeReqSent = True
