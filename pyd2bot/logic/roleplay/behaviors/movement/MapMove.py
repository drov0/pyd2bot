import threading
from time import perf_counter

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.movement.RequestMapData import \
    RequestMapData
from pydofus2.com.ankamagames.atouin.managers.MapDisplayManager import \
    MapDisplayManager
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
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
from pydofus2.com.ankamagames.dofus.network.messages.game.context.GameMapMovementRequestMessage import \
    GameMapMovementRequestMessage
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.pathfinding.Pathfinding import \
    Pathfinding
from pydofus2.com.ankamagames.jerakine.types.positions.MapPoint import MapPoint
from pydofus2.com.ankamagames.jerakine.types.positions.MovementPath import \
    MovementPath


class MapMove(AbstractBehavior):
    CONSECUTIVE_MOVEMENT_DELAY = 0.25
    MOVE_REQ_TIMEOUT = 7
    ALREADY_ONCELL = 7001

    def __init__(self) -> None:
        super().__init__()

    def run(self, destCell, exactDistination=True) -> None:
        Logger().info(f"Move from {PlayedCharacterManager().currentCellId} to {destCell} started")
        self.exactDestination = exactDistination
        if isinstance(destCell, int):
            self.dstCell = MapPoint.fromCellId(destCell)
        elif isinstance(destCell, MapPoint):
            self.dstCell = destCell
        else:
            self.finish(False, "Invalid destination cell")
        self.move()

    def stop(self) -> None:
        if PlayedCharacterManager().entity and PlayedCharacterManager().entity.isMoving:
            PlayedCharacterManager().entity.stop()
        KernelEventsManager().clearAllByOrigin(self)
        MapMove.clear()

    def move(self) -> bool:
        rpmframe: "RoleplayMovementFrame" = Kernel().worker.getFrameByName("RoleplayMovementFrame")
        if not rpmframe:
            return KernelEventsManager().onceFramePushed("RoleplayMovementFrame", self.move, originator=self)
        playerEntity = DofusEntities().getEntity(PlayedCharacterManager().id)
        self.errMsg = f"Move to cell {self.dstCell} failed for reason %s"
        if playerEntity is None:
            return self.fail(MovementFailError.PLAYER_NOT_FOUND)
        currentCellId = playerEntity.position.cellId
        if MapDisplayManager().dataMap is None:
            return self.fail(MovementFailError.MAP_NOT_LOADED)
        if currentCellId == self.dstCell.cellId:
            Logger().info(f"Destination cell {self.dstCell.cellId} is the same as the current player cell")
            return self.finish(self.ALREADY_ONCELL, None)
        if PlayerLifeStatusEnum(PlayedCharacterManager().state) == PlayerLifeStatusEnum.STATUS_TOMBSTONE:
            return self.fail(MovementFailError.PLAYER_IS_DEAD)
        self.movePath = Pathfinding().findPath(playerEntity.position, self.dstCell)
        if self.movePath is None:
            return self.fail(MovementFailError.NO_PATH_FOUND)
        if len(self.movePath) == 0 or (self.exactDestination and self.movePath.end.cellId != self.dstCell.cellId):
            return self.fail(MovementFailError.CANT_REACH_DEST_CELL)
        self.countMoveFail = 0
        self.requestMovement()

    def fail(self, reason: MovementFailError) -> None:
        self.finish(reason, self.errMsg % reason.name)

    def requestMovement(self) -> None:
        if len(self.movePath) == 0:
            return self.finish(True, None)
        self.once(
            KernelEvent.MOVE_REQUEST_REJECTED,
            callback=lambda event: self.onMoveRequestReject(MovementFailError.MOVE_REQUEST_REJECTED),
        )
        KernelEventsManager().onceEntityMoved(
            PlayedCharacterManager().id,
            callback=self.onPlayerMoving,
            timeout=15,
            ontimeout=lambda listener: self.onMoveRequestReject(MovementFailError.MOVE_REQUEST_TIMEOUT),
            originator=self, 
        )
        self.sendMoveRequest()

    def onMoveRequestReject(self, reason: MovementFailError) -> None:
        self.countMoveFail += 1
        if self.countMoveFail > 10:
            return self.fail(reason)
        Logger().warning(f"server rejected movement for reason {reason.name}")
        KernelEventsManager().clearAllByOrigin(self)
        RequestMapData().start(callback=lambda code, error: self.move())

    def sendMoveRequest(self):
        gmmrmsg = GameMapMovementRequestMessage()
        gmmrmsg.init(self.movePath.keyMoves(), MapDisplayManager().currentMapPoint.mapId)
        ConnectionsHandler().send(gmmrmsg)
        Logger().info(f"Requested move from {PlayedCharacterManager().currentCellId} to {self.dstCell.cellId}")

    def onPlayerMoving(self, event, clientMovePath: MovementPath):
        Logger().info(f"Move request accepted.")
        if clientMovePath.end.cellId != self.dstCell.cellId:
            Logger().warning(f"Landed on cell {clientMovePath.end.cellId} not dst {self.dstCell.cellId}!")
        self.once(
            KernelEvent.PLAYER_MOVEMENT_COMPLETED, callback=self.onMovementCompleted
        )

    def onMovementCompleted(self, event, success):
        if success:
            self.finish(success, None)
        else:
            self.finish(success, "Player movement was stopped")
