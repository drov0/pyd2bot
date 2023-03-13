from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.MapMove import MapMove
from pyd2bot.logic.roleplay.behaviors.RequestMapData import RequestMapData
from pydofus2.com.ankamagames.atouin.managers.MapDisplayManager import \
    MapDisplayManager
from pydofus2.com.ankamagames.berilia.managers.EventsHandler import Event, Listener
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayInteractivesFrame import (
    InteractiveElementData, RoleplayInteractivesFrame
)
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
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.ChangeMapMessage import \
    ChangeMapMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.MapInformationsRequestMessage import \
    MapInformationsRequestMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.interactive.InteractiveUseRequestMessage import \
    InteractiveUseRequestMessage
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.types.positions.MapPoint import MapPoint


class ChangeMap(AbstractBehavior):
    MAPCHANGE_TIMEOUT = 5
    REQUEST_MAPDATA_TIMEOUT = 3

    def __init__(self) -> None:
        super().__init__()
        self.requestTimer = None
        self.transition = None
        self.mapChangeRequestNbrFails = 0
        self.changeMapRejectListener: 'Listener' = None
        self.mapChangeListener: 'Listener' = None
        self.changeMapRejectListener: 'Listener' = None
        self.mapChangeIE: InteractiveElementData = None
        self.mapChangeCellId: int = None

    def start(self, transition: Transition=None, edge: Edge=None, dstMapId=None, callback=None):
        if self.running.is_set():
            return self.finish(False, f"Already changing map to {self.dstMapId}!")
        self.running.set()
        self.callback = callback
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
    
    def followEdge(self):
        for tr in self.edge.transitions:
            if tr.isValid:
                self.transition = tr
                return self.followTransition()
        self.finish(False, "No valid transition found!")

    def getTransitionIe(self, transition: Transition, callback) -> "InteractiveElementData":
        if not self.rpiframe:
            return KernelEventsManager().onceFramePushed("RoleplayInteractivesFrame", self.getTransitionIe, [transition])
        callback(self.rpiframe.getInteractiveElement(transition.id, transition.skillId))

    def followTransition(self):
        if not self.transition.isValid:
            return self.finish(False, "Trying to follow a non valid transition")
        if self.dstMapId == PlayedCharacterManager().currentMap.mapId:
            return self.finish(True, None)
        trType = TransitionTypeEnum(self.transition.type)
        if trType == TransitionTypeEnum.INTERACTIVE:
            def onTransitionIE(ie: InteractiveElementData):
                if not ie:
                    return self.finish(False, f"InteractiveElement {self.transition.id} not found")
                self.mapChangeIE = ie
                iePosition, useInteractive = self.worldframe.getNearestCellToIe(self.mapChangeIE.element, self.mapChangeIE.position)
                if not useInteractive:
                    return self.finish(False, "Cannot use the interactive")
                Logger().info(f"[ChangeMap] Interactive Map change using skill '{ie.skillUID}' on cell '{ie.position.cellId}'")
                self.mapChangeCellId = iePosition.cellId
                self.interactiveMapChange()
            self.getTransitionIe(self.transition, onTransitionIE)
        else:
            self.mapChangeCellId = self.transition.cell
            self.scrollMapChange()

    def onMapRequestFailed(self, reason: MovementFailError):
        Logger().warning(f"[ChangeMap] request failed for reason: {reason.name}")
        self.mapChangeRequestNbrFails += 1
        if self.mapChangeRequestNbrFails > 3:
            self.mapChangeListener.delete()
            return self.finish(reason, f"Change map failed for reason: {reason.name}")
        self.mapChangeListener.armTimer()
        self.followTransition()

    def onRequestRejectedByServer(self, event: Event, reason: MovementFailError):
        Logger().debug(f"[ChangeMap] server reject called by event {event.name}.")
        self.mapChangeListener.cancelTimer()
        def onResult(errCode, error):
            if error:
                return self.finish(False, error)
            self.onMapRequestFailed(reason)
        RequestMapData().start(onResult)
    
    def onDestMapProcessedTimeout(self, listener: Listener):
        listener.delete()
        self.finish(False, "Request Map data timeout")
        
    def onCurrentMap(self, event: Event, mapId):
        if mapId == self.dstMapId:
            self.changeMapRejectListener.delete()
            KernelEventsManager().onceMapProcessed(
                lambda: self.finish(True, None),
                mapId=self.dstMapId,
                timeout=10,
                ontimeout=self.onDestMapProcessedTimeout
            )
            return
        Logger().error(f"Received new mapId {mapId}, different from dest {self.dstMapId}")

    def changeMap(self, requestRejectedEvent, movementError, exactDestination):
        ttype = TransitionTypeEnum(self.transition.type)
        Logger().info(f"{ttype.name} map change {self.dstMapId}")
        def onMoveToMapChangeCell(errType, error):
            if error:
                return self.finish(errType, error)
            if errType == "on same cell" and TransitionTypeEnum(self.transition.type) == TransitionTypeEnum.MAP_ACTION:
                currMp = MapPoint.fromCellId(PlayedCharacterManager().currentCellId)
                for x, y in currMp.iterChilds():
                    def onMoved(errType, err):
                        if err:
                            self.mapChangeListener.delete()
                            self.changeMapRejectListener.delete()
                            self.finish(errType, err)
                        self.changeMap(requestRejectedEvent, movementError, exactDestination)
                    mp = MapPoint.fromCoords(x, y)
                    return MapMove().start(mp.cellId, onMoved, exactDestination)
            self.mapChangeListener = KernelEventsManager().once(
                KernelEvent.CURRENT_MAP,
                self.onCurrentMap,
                timeout=self.MAPCHANGE_TIMEOUT,
                ontimeout=lambda _: self.onMapRequestFailed(MovementFailError.MAPCHANGE_TIMEOUT)
            )
            self.changeMapRejectListener = KernelEventsManager().once(
                requestRejectedEvent, 
                lambda event: self.onRequestRejectedByServer(event, movementError)
            )
            if TransitionTypeEnum(self.transition.type) != TransitionTypeEnum.MAP_ACTION:
                self.requestMapChange()
        MapMove().start(self.mapChangeCellId, onMoveToMapChangeCell, exactDestination)

    def scrollMapChange(self):
        requestRejectedEvent = KernelEvent.MOVE_REQUEST_REJECTED
        movementError = MovementFailError.MOVE_REQUEST_REJECTED
        exactDestination = True
        self.changeMap(requestRejectedEvent, movementError, exactDestination)            

    def interactiveMapChange(self):
        requestRejectedEvent = KernelEvent.INTERACTIVE_USE_ERROR
        movementError = MovementFailError.INTERACTIVE_USE_ERROR
        exactDestination = False
        self.changeMap(requestRejectedEvent, movementError, exactDestination)            

    def requestMapChange(self):
        if TransitionTypeEnum(self.transition.type) == TransitionTypeEnum.INTERACTIVE:
            iurmsg = InteractiveUseRequestMessage()
            iurmsg.init(int(self.mapChangeIE.element.elementId), int(self.mapChangeIE.skillUID))
            ConnectionsHandler().send(iurmsg)
        else:
            cmmsg = ChangeMapMessage()
            cmmsg.init(int(self.transition.transitionMapId), False)
            ConnectionsHandler().send(cmmsg)
