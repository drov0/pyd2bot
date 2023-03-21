import threading
from time import perf_counter

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.RequestMapData import RequestMapData
from pydofus2.com.ankamagames.atouin.managers.MapDisplayManager import \
    MapDisplayManager
from pydofus2.com.ankamagames.berilia.managers.EventsHandler import (Event,
                                                                     Listener)
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.logic.game.common.misc.DofusEntities import \
    DofusEntities
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayMovementFrame import \
    RoleplayMovementFrame
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.types.MovementFailError import \
    MovementFailError
from pydofus2.com.ankamagames.dofus.network.enums.PlayerLifeStatusEnum import \
    PlayerLifeStatusEnum
from pydofus2.com.ankamagames.dofus.network.messages.common.basic.BasicPingMessage import \
    BasicPingMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.GameMapMovementCancelMessage import \
    GameMapMovementCancelMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.GameMapMovementConfirmMessage import \
    GameMapMovementConfirmMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.GameMapMovementRequestMessage import \
    GameMapMovementRequestMessage
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.pathfinding.Pathfinding import \
    Pathfinding
from pydofus2.com.ankamagames.jerakine.types.enums.DirectionsEnum import \
    DirectionsEnum
from pydofus2.com.ankamagames.jerakine.types.positions.MapPoint import MapPoint
from pydofus2.com.ankamagames.jerakine.types.positions.MovementPath import \
    MovementPath


class MovementAnimation(threading.Thread):
    
    def __init__(self, clientMovePath: MovementPath, callback):
        super().__init__(name=threading.currentThread().name)
        self.movePath = clientMovePath
        self.currStep = self.movePath.path[0]
        self.stopEvt = threading.Event()
        self.running = threading.Event()
        self.callback = callback
        
    def stop(self):
        self.stopEvt.set()

    def isRunning(self):
        return self.running.is_set()

    def run(self):
        Logger().info(f"[MapMove] Movement animation started at cell {self.currStep.cellId}")
        self.running.set()
        for pe in self.movePath.path[1:] + [self.movePath.end]:
            if Kernel().worker.terminated.is_set():
                return Logger().warning("Stoped movement anim woz worker terminated")
            stepDuration = self.getStepDuration(self.currStep.orientation)
            if self.stopEvt.wait(stepDuration):
                Logger().warning(f"[MapMove] Movement animation stopped")
                canceledMoveMessage = GameMapMovementCancelMessage()
                canceledMoveMessage.init(pe.cellId)
                ConnectionsHandler().send(canceledMoveMessage)
                self.running.clear()
                return
            Logger().info(f"[MapMove] Reached cell {pe.cellId}")
            self.currStep = pe
        Logger().info(f"[MapMove] Movement animation ended")
        if self.stopEvt.wait(0.2):
            return
        gmmcmsg = GameMapMovementConfirmMessage()
        ConnectionsHandler().send(gmmcmsg)
        self.running.clear()
        self.callback(True)
            
    def getStepDuration(self, orientation) -> float:
        if PlayedCharacterManager().inventoryWeightMax != 0:
            weightCoef = PlayedCharacterManager().inventoryWeight / PlayedCharacterManager().inventoryWeightMax
        else:
            weightCoef = 0
        canRun = weightCoef < 1.0
        if isinstance(orientation, DirectionsEnum):
            orientation = orientation.value
        if not canRun:
            if orientation % 2 == 0:
                if orientation % 4 == 0:
                    duration = self.movePath.WALK_HORIZONTAL_DIAG_DURATION
                duration = self.movePath.WALK_VERTICAL_DIAG_DURATION
            duration = self.movePath.WALK_LINEAR_DURATION
        else:
            if orientation % 2 == 0:
                if orientation % 4 == 0:
                    duration = self.movePath.RUN_HORIZONTAL_DIAG_DURATION
                duration = self.movePath.RUN_VERTICAL_DIAG_DURATION
            duration = self.movePath.RUN_LINEAR_DURATION
        return duration / 1000

class MapMove(AbstractBehavior):
    CONSECUTIVE_MOVEMENT_DELAY = 0.25
    MOVE_REQ_TIMEOUT = 1
    NEXT_MOVE_TIME = dict[str, int]()
    ALREADY_ONCELL = 7001

    def __init__(self) -> None:
        self.movementAnimation: MovementAnimation = None
        self.moveListener: Listener = None
        self.moveRejectListener: Listener = None
        self.countMoveFail = 0
        super().__init__()
    
    def run(self, destCell, exactDistination=True) -> None:
        Logger().info(f"[MapMove] from {PlayedCharacterManager().currentCellId} to cell {destCell} started")
        self.exactDestination = exactDistination
        if isinstance(destCell, int):
            self.dstCell = MapPoint.fromCellId(destCell)
        elif isinstance(destCell, MapPoint):
            self.dstCell = destCell
        else:
            self.finish(False, "[MapMove] Invalid destination cell")
        self.move()

    def stop(self) -> None:
        if self.movementAnimation:
            self.movementAnimation.stop()
            self.movementAnimation.join()
        if self.moveListener:
            self.moveListener.delete()
        if self.moveRejectListener:
            self.moveRejectListener.delete()
        MapMove.clear()

    def move(self) -> bool:
        rpmframe: "RoleplayMovementFrame" = Kernel().worker.getFrameByName("RoleplayMovementFrame")
        if not rpmframe:
            return KernelEventsManager().onceFramePushed("RoleplayMovementFrame", self.move, originator=self)
        playerEntity = DofusEntities().getEntity(PlayedCharacterManager().id)
        self.errMsg = f"[MapMove] Move to cell {self.dstCell} failed for reason %s"        
        if playerEntity is None:
            return self.fail(MovementFailError.PLAYER_NOT_FOUND)
        currentCellId = playerEntity.position.cellId
        if MapDisplayManager().dataMap is None:
            return self.fail(MovementFailError.MAP_NOT_LOADED)
        if currentCellId == self.dstCell.cellId:
            Logger().info(f"[MapMove] Destination cell {self.dstCell.cellId} is the same as the current player cell")
            return self.finish(self.ALREADY_ONCELL, None)
        if PlayerLifeStatusEnum(PlayedCharacterManager().state) == PlayerLifeStatusEnum.STATUS_TOMBSTONE:
            return self.fail(MovementFailError.PLAYER_IS_DEAD)
        self.movePath = Pathfinding().findPath(playerEntity.position, self.dstCell)
        if self.movePath is None:
            return self.fail(MovementFailError.NO_PATH_FOUND)
        if len(self.movePath) == 0:
            return self.finish(True, None)
        if self.exactDestination and self.movePath.end.cellId != self.dstCell.cellId:
            return self.fail(MovementFailError.CANT_REACH_DEST_CELL)
        self.requestMovement()
        return True

    def fail(self, reason: MovementFailError) -> None:
        if self.moveListener:
            self.moveListener.delete()
        if self.moveRejectListener:
            self.moveRejectListener.delete()
        self.finish(reason, self.errMsg % reason.name)
        
    def requestMovement(self) -> None:
        if len(self.movePath) == 0:
            return self.finish(True, None)
        self.moveRejectListener = KernelEventsManager().once(
            KernelEvent.MOVE_REQUEST_REJECTED, 
            lambda event: self.onMoveRequestReject(MovementFailError.MOVE_REQUEST_REJECTED), originator=self
        )
        self.moveListener = KernelEventsManager().onceEntityMoved(
            PlayedCharacterManager().id, 
            self.onMoveRequestAccepted,
            timeout=2,
            ontimeout=lambda listener: self.onMoveRequestReject(MovementFailError.MOVE_REQUEST_TIMEOUT), originator=self
        )
        self.sendMoveRequest()
        
    def onMoveRequestReject(self, reason: MovementFailError) -> None:        
        gmmcmsg = GameMapMovementConfirmMessage()
        ConnectionsHandler().send(gmmcmsg)
        pingMsg = BasicPingMessage()
        pingMsg.init(True)
        ConnectionsHandler().send(pingMsg)
        self.countMoveFail += 1
        if self.countMoveFail > 10:
            return self.fail(reason)
        Logger().warning(f"[MapMove] server reject for reason {reason.name}")
        self.moveListener.delete()
        self.moveRejectListener.delete()
        RequestMapData().start(callback=lambda code, error: self.move())

    def sendMoveRequest(self):
        gmmrmsg = GameMapMovementRequestMessage()
        gmmrmsg.init(self.movePath.keyMoves(), MapDisplayManager().currentMapPoint.mapId)    
        nextMoveTime = MapMove.NEXT_MOVE_TIME.get(PlayedCharacterManager().instanceId)
        if nextMoveTime is not None:
            diff = nextMoveTime - perf_counter()
            if diff > 0:
                if Kernel().worker.terminated.wait(diff):
                    return Logger().warning("Worker terminated while move behavior running")
        ConnectionsHandler().send(gmmrmsg)
        Logger().info(f"[MapMove] Requested move from {PlayedCharacterManager().currentCellId} to {self.dstCell.cellId}")
        MapMove.NEXT_MOVE_TIME[PlayedCharacterManager().instanceId] = perf_counter() + self.CONSECUTIVE_MOVEMENT_DELAY

    def onMoveRequestAccepted(self, event: Event, clientMovePath: MovementPath):
        self.moveRejectListener.delete()
        Logger().info(f"[MapMove] Move request accepted.")
        if clientMovePath.end.cellId != self.dstCell.cellId:
            Logger().warning(f"[MapMove] Landed on cell {clientMovePath.end.cellId} not on dst {self.dstCell.cellId}!") 
        self.movementAnimation = MovementAnimation(clientMovePath, lambda success: self.finish(success, None))
        self.movementAnimation.start()