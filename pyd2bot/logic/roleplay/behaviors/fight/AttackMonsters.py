from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.movement.MapMove import MapMove
from pyd2bot.logic.roleplay.behaviors.movement.RequestMapData import \
    RequestMapData
from pydofus2.com.ankamagames.berilia.managers.EventsHandler import (Event,
                                                                     Listener)
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.fight.GameRolePlayAttackMonsterRequestMessage import \
    GameRolePlayAttackMonsterRequestMessage
from pydofus2.com.ankamagames.dofus.network.types.game.context.GameContextActorInformations import \
    GameContextActorInformations
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.types.positions.MapPoint import MapPoint
from pydofus2.com.ankamagames.jerakine.types.positions.MovementPath import \
    MovementPath

""" 
A map is a grid, it contains special cells (MAP_ACTION cells), that allows to go to adjacent maps.
An Entity in the game can be in only one map and one cell at a time.
Monster Entities spawn and move around randomly in these maps, any player may attack them.
Once a player attacks a monster no other player can attack it.
This script automates the processed of attacking a monster.
As input of this script, we have the entityId of the monster, from its id at any point we can retrieve its data, that contains its current cell. 
If no data about monster is found, it means the monster vanished because another player attacked it.
Corner cases:
- Monster vanishes while moving towards it -> Stop movement and start and return monster vanished error
- Monster moves while moving towards it -> Stop movement and restart script
- Monster vanishes after sending attack request -> return monster vanished error
- Monster moves after sending attack request -> wait to see if server will still accept request, if timeout restart script
- Monster vanishes or moves and player lands on MAP_ACTION cell -> return player changed map error
"""


class AttackMonsters(AbstractBehavior):
    ENTITY_VANISHED = 801
    ENTITY_MOVED = 802
    MAP_CHANGED = 803
    FIGHT_REQ_TIMEDOUT = 804
    FIGHT_REQ_TIMEOUT = 7

    def __init__(self) -> None:
        super().__init__()
        self.entityMovedListener: Listener = None
        self.fightShwordListener: Listener = None
        self.attackMonsterListener: Listener = None
        self.mapChangeListener: Listener = None
        self.nbrFails = 0

    @property
    def entityInfo(self) -> "GameContextActorInformations":
        return Kernel().entitiesFrame.getEntityInfos(self.entityId)
    
    def getEntityCellId(self) -> int:
        if not self.entityInfo:
            return None
        return self.entityInfo.disposition.cellId

    def run(self, entityId):
        self.entityId = entityId
        cellId = self.getEntityCellId()
        if not cellId:
            return self.finish(self.ENTITY_VANISHED, "Entity no more on the map")
        self.entityMovedListener = KernelEventsManager().onEntityMoved(self.entityId, self.onEntityMoved, originator=self)
        self.fightShwordListener = KernelEventsManager().onceFightSword(
            self.entityId, cellId, self.onFightWithEntityTaken, originator=self
        )
        self.mapChangeListener = KernelEventsManager().on(KernelEvent.CurrentMap, self.onCurrentMap, originator=self)
        self._start()

    def _start(self):
        if not Kernel().entitiesFrame:
            return KernelEventsManager().onceFramePushed("RoleplayEntitiesFrame", self._start, originator=self)
        cellId = self.getEntityCellId()
        if not cellId:
            return self.finish(self.ENTITY_VANISHED, "Entity not more on the map")
        Logger().info(f"[AttackMonsters] Moving to monster {self.entityId} cell {cellId}")
        MapMove().start(MapPoint.fromCellId(cellId), callback=self.onEntityReached, parent=self)

    def onFightWithEntityTaken(self):
        if MapMove().isRunning():
            error = "Entity vanished while moving towards it!"
            MapMove().stop()
        elif self.attackMonsterListener:
            error = "Entity vanished while attacking it"
        return self.finish(self.ENTITY_VANISHED, error)

    def onEntityReached(self, status, error):
        if error:
            return self.finish(status, error)
        Logger().info(f"[AttackMonsters] Reached monster group cell")
        self.attackMonsterListener = KernelEventsManager().once(
            event_id=KernelEvent.FightStarted,
            callback=lambda event: self.finish(True, None), 
            timeout=self.FIGHT_REQ_TIMEOUT, 
            ontimeout=self.finish, 
            retryNbr=3,
            retryAction=self.restart,
            originator=self
        )
        self.requestAttackMonsters()

    def onEntityMoved(self, event: Event, movePath: MovementPath):
        Logger().warning(f"[AttackMonsters] Entity moved to cell {movePath.end.cellId}")
        if MapMove().isRunning():
            MapMove().stop()
        elif self.attackMonsterListener:
            Logger().warning("Entity moved but we already asked server for attack")
            return
        self.restart()
        
    def restart(self):
        KernelEventsManager().clearAllByOrigin(self)
        RequestMapData().start(callback=lambda code, err: self._start(), parent=self)

    def requestAttackMonsters(self) -> None:
        grpamrmsg = GameRolePlayAttackMonsterRequestMessage()
        grpamrmsg.init(self.entityId)
        ConnectionsHandler().send(grpamrmsg)

    def onCurrentMap(self, event, mapId):
        Logger().warning("Monster moved and was on a Map action cell, we changed to a new map")
        self.finish(self.MAP_CHANGED, "Map changed after landing on entity cell")
