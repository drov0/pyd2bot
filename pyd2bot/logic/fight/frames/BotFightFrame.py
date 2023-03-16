import threading
from queue import PriorityQueue
from time import perf_counter
from types import FunctionType
from typing import TYPE_CHECKING, Tuple

from pyd2bot.logic.fight.messages.MuleSwitchedToCombatContext import \
    MuleSwitchedToCombatContext
from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.misc.BotEventsmanager import BotEventsManager
from pyd2bot.thriftServer.pyd2botService.ttypes import Character
from pydofus2.com.ankamagames.atouin.AtouinConstants import AtouinConstants
from pydofus2.com.ankamagames.atouin.managers.EntitiesManager import \
    EntitiesManager
from pydofus2.com.ankamagames.atouin.utils.DataMapProvider import \
    DataMapProvider
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.datacenter.effects.EffectInstance import \
    EffectInstance
from pydofus2.com.ankamagames.dofus.datacenter.monsters.Monster import Monster
from pydofus2.com.ankamagames.dofus.datacenter.spells.Spell import Spell
from pydofus2.com.ankamagames.dofus.internalDatacenter.spells.SpellWrapper import \
    SpellWrapper
from pydofus2.com.ankamagames.dofus.internalDatacenter.stats.EntityStats import \
    EntityStats
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.logic.common.managers.StatsManager import \
    StatsManager
from pydofus2.com.ankamagames.dofus.logic.game.common.frames.SpellInventoryManagementFrame import \
    SpellInventoryManagementFrame
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.logic.game.fight.managers.BuffManager import \
    BuffManager
from pydofus2.com.ankamagames.dofus.logic.game.fight.managers.CurrentPlayedFighterManager import \
    CurrentPlayedFighterManager
from pydofus2.com.ankamagames.dofus.logic.game.fight.miscs.FightReachableCellsMaker import \
    FightReachableCellsMaker
from pydofus2.com.ankamagames.dofus.logic.game.fight.miscs.TackleUtil import \
    TackleUtil
from pydofus2.com.ankamagames.dofus.network.enums.FightOptionsEnum import \
    FightOptionsEnum
from pydofus2.com.ankamagames.dofus.network.messages.game.actions.fight.GameActionFightCastRequestMessage import \
    GameActionFightCastRequestMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.actions.fight.GameActionFightNoSpellCastMessage import \
    GameActionFightNoSpellCastMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.actions.sequence.SequenceEndMessage import \
    SequenceEndMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.actions.sequence.SequenceStartMessage import \
    SequenceStartMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.fight.character.GameFightShowFighterMessage import \
    GameFightShowFighterMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.fight.GameFightEndMessage import \
    GameFightEndMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.fight.GameFightJoinMessage import \
    GameFightJoinMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.fight.GameFightOptionStateUpdateMessage import \
    GameFightOptionStateUpdateMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.fight.GameFightOptionToggleMessage import \
    GameFightOptionToggleMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.fight.GameFightReadyMessage import \
    GameFightReadyMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.fight.GameFightTurnEndMessage import \
    GameFightTurnEndMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.fight.GameFightTurnFinishMessage import \
    GameFightTurnFinishMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.fight.GameFightTurnReadyMessage import \
    GameFightTurnReadyMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.fight.GameFightTurnReadyRequestMessage import \
    GameFightTurnReadyRequestMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.fight.GameFightTurnResumeMessage import \
    GameFightTurnResumeMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.fight.GameFightTurnStartMessage import \
    GameFightTurnStartMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.fight.GameFightTurnStartPlayingMessage import \
    GameFightTurnStartPlayingMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.GameMapMovementRequestMessage import \
    GameMapMovementRequestMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.GameMapNoMovementMessage import \
    GameMapNoMovementMessage
from pydofus2.com.ankamagames.dofus.network.types.game.context.fight.GameFightFighterInformations import \
    GameFightFighterInformations
from pydofus2.com.ankamagames.dofus.network.types.game.context.fight.GameFightMonsterInformations import \
    GameFightMonsterInformations
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.messages.Frame import Frame
from pydofus2.com.ankamagames.jerakine.messages.Message import Message
from pydofus2.com.ankamagames.jerakine.pathfinding.Pathfinding import \
    Pathfinding
from pydofus2.com.ankamagames.jerakine.types.enums.Priority import Priority
from pydofus2.com.ankamagames.jerakine.types.positions.MapPoint import MapPoint
from pydofus2.com.ankamagames.jerakine.types.positions.MovementPath import \
    MovementPath
from pydofus2.com.ankamagames.jerakine.types.zones.Cross import Cross
from pydofus2.com.ankamagames.jerakine.types.zones.IZone import IZone
from pydofus2.com.ankamagames.jerakine.types.zones.Lozenge import Lozenge
from pydofus2.com.ankamagames.jerakine.utils.display.spellZone.SpellShapeEnum import \
    SpellShapeEnum
from pydofus2.damageCalculation.tools.StatIds import StatIds
from pydofus2.mapTools import MapTools

lock = threading.Lock()
if TYPE_CHECKING:
    pass
class Target:
    
    def __init__(self, entity: GameFightMonsterInformations, cellId: int) -> None:
        self.entity = entity
        self.pos = MapPoint.fromCellId(entity.disposition.cellId)
        self.entityId = entity.contextualId
        self.distFromPlayer = self.pos.distanceToCellId(cellId)

    def __str__(self) -> str:
        return f"({self.entity.contextualId}, { self.entity.disposition.cellId}, {self.distFromPlayer})"

class BotFightFrame(Frame):
    VERBOSE = True
    ACTION_TIMEOUT = 7
    CONSECUTIVE_MOVEMENT_DELAY: int = 0.25
    _average_time_to_find_path = 0
    _number_of_path_calculations = 0
    _total_time_to_find_path = 0

    def __init__(self):
        self.init()
        super().__init__()

    def init(self):
        self._turnAction = list[FunctionType]()
        self._spellCastFails = 0
        self._inFight = False
        self._fightCount: int = 0
        self._lastTarget: int = None
        self._spellw: SpellWrapper = None
        self._spellShape = None
        self._myTurn = False
        self._currentPath = None
        self._currentTarget = None
        self._wantcastSpell = None
        self.currentPlayer = None
        self._lastPlayerId = None
        self._reachableCells = None
        self._seqQueue = []
        self._waitingSeqEnd = False
        self._turnPlayed = 0
        self._isRequestingMovement = False
        self._requestingCastSpell = False
        self.fightReadySent = False
        self._confirmTurnEnd = False
        self._moveRequestFails = 0
        self._lastMoveRequestTime = None
        self._forbidenCells = set()
        self._turnStartPlaying = False
        self._suspectedUnreachableCell = None
        self.fightResumed = False
        KernelEventsManager().on(KernelEvent.TEXT_INFO, self.onServerTextInfo, originator=self)
        KernelEventsManager().once(KernelEvent.FIGHT_RESUMED, self.onFightResumed, originator=self)

    def onFightResumed(self, event):
        self.fightResumed = True

    def pushed(self) -> bool:
        self.init()
        return True

    @property
    def playerStats(self) -> "EntityStats":
        return StatsManager().getStats(self.currentPlayer.id)

    @property
    def spellId(self) -> int:
        return BotConfig().getPrimarySpellId(self.currentPlayer.breedId)

    @property
    def playerManager(self) -> "PlayedCharacterManager":
        if not self.currentPlayer:
            Logger().warning("Asking for player manager for None current player")
            return None
        return PlayedCharacterManager.getInstance(self.currentPlayer.login)

    @property
    def fightCount(self) -> int:
        return self._fightCount

    @property
    def connection(self) -> "ConnectionsHandler":
        return ConnectionsHandler.getInstance(self.currentPlayer.login)
    
    def pulled(self) -> bool:
        self._spellw = None
        if self._reachableCells:
            self._reachableCells.clear()
        self._turnAction.clear()
        KernelEventsManager().clearAllByOrigin(self)
        return True

    @property
    def priority(self) -> int:
        return Priority.VERY_LOW

    def buildPath(self, parentOfcell: dict[int, int], endCellId):
        path = [endCellId]
        currCellId = endCellId
        while True:
            currCellId = parentOfcell.get(currCellId)
            if currCellId is None:
                break
            path.append(currCellId)
        path.reverse()
        return path

    def findCellsWithLosToTargets(self, spellw: SpellWrapper, targets: list[Target], fighterCell: int) -> list[int]:
        hasLosToTargets = dict[int, list[Target]]()
        s = perf_counter()
        spellZone = self.getSpellZone(spellw)
        maxRangeFromFighter = 0
        for target in targets:
            currSpellZone = spellZone.getCells(target.pos.cellId)
            for cell in currSpellZone:
                p = MapPoint.fromCellId(cell)
                line = MapTools.getMpLine(target.pos.cellId, p.cellId)
                los = True
                if len(line) > 1:
                    for mp in line[:-1]:
                        if not DataMapProvider().pointLos(mp.x, mp.y, False):
                            los = False
                            break
                if los:
                    if fighterCell == p.cellId:
                        return 0, {fighterCell: [target]}
                    if p.cellId not in hasLosToTargets:
                        hasLosToTargets[p.cellId] = list[Target]()
                    hasLosToTargets[p.cellId].append(target)
                    maxRangeFromFighter = max(maxRangeFromFighter, target.distFromPlayer)
        Logger().info(f"findCellsWithLosToTargets took {perf_counter() - s} seconds")
        return maxRangeFromFighter, hasLosToTargets

    def findPathToTarget(self, spellw: SpellWrapper, targets: list[Target]) -> Tuple[Target, list[int]]:
        if not targets:
            return None, None
        for target in targets:
            if target.pos.distanceTo(self.fighterPos) <= 1:
                return target, []
        maxRangeFromFighter, hasLosToTargets = self.findCellsWithLosToTargets(spellw, targets, self.fighterPos.cellId)
        if not hasLosToTargets:
            return None, None
        if self.fighterPos.cellId in hasLosToTargets:
            return hasLosToTargets[self.fighterPos.cellId][0], []
        if self.movementPoints <= 0:
            return None, None
        reachableCells = set(
            FightReachableCellsMaker(self.fighterInfos, self.fighterPos.cellId, maxRangeFromFighter).reachableCells
        )
        queue = PriorityQueue[Tuple[int, int, int]]()
        queue.put((0, 0, self.fighterPos.cellId))
        visited = set()
        parentOfCell = {}
        bestAlternative = None
        BtestAlternativeCost = float("inf")
        while not queue.empty():
            _, usedPms, currCellId = queue.get()
            if currCellId in visited:
                continue
            visited.add(currCellId)
            currPoint = MapPoint.fromCellId(currCellId)
            for nextMapPoint in currPoint.vicinity():
                nextCellId = nextMapPoint.cellId
                if nextCellId not in self._forbidenCells and nextCellId not in visited and nextCellId in reachableCells:
                    parentOfCell[nextCellId] = currCellId
                    if nextCellId in hasLosToTargets:
                        path = self.buildPath(parentOfCell, nextCellId)
                        return hasLosToTargets[nextCellId][0], path
                    heuristic = (
                        usedPms
                        + 1
                        + 10
                        * sum([MapTools.getDistance(nextCellId, cellId) for cellId in hasLosToTargets])
                        / len(hasLosToTargets)
                    )
                    if heuristic < BtestAlternativeCost:
                        bestAlternative = nextCellId
                        BtestAlternativeCost = heuristic
                    queue.put((heuristic, usedPms + 1, nextCellId))
        if bestAlternative is not None:
            path = self.buildPath(parentOfCell, bestAlternative)
            return None, path
        return None, None

    @classmethod
    def updateAveragePathTime(cls, time: float):
        with lock:
            cls._total_time_to_find_path += time
            cls._number_of_path_calculations += 1
            cls._average_time_to_find_path = cls._total_time_to_find_path / cls._number_of_path_calculations
            if cls._number_of_path_calculations > 100:
                cls._total_time_to_find_path = 0
                cls._number_of_path_calculations = 0

    def onInvisibleMobBlockingWay(self):
        self._turnAction.clear()
        self.addTurnAction(self.turnEnd, [])
        self.nextTurnAction("Invisible mob blocking way")

    def getTargetableEntities(self, spellw: SpellWrapper, targetSum=False) -> list[Target]:
        result = list[Target]()
        infosTable = []
        if not Kernel().fightEntitiesFrame or not Kernel().battleFrame:
            Logger().error("entitiesFrame or battleFrame is not found")
            return []
        if self.fighterInfos is None:
            Logger().warning("Fighter not found")
            return []
        for entity in Kernel().fightEntitiesFrame.entities.values():
            if entity.contextualId < 0:
                monster = entity
                canCast, reason = self.canCastSpell(entity.contextualId)
                stats = StatsManager().getStats(entity.contextualId)
                hp = stats.getHealthPoints()
                stats.getMaxHealthPoints()
                ismonster = isinstance(entity, GameFightMonsterInformations)
                name = "unknown"
                level = "unknwon"
                if isinstance(entity, GameFightMonsterInformations):
                    monster = Monster.getMonsterById(entity.creatureGenericId)
                    name = monster.name
                    level = entity.creatureLevel
                entry = {
                    "name": name,
                    "level": level,
                    "teamId": entity.spawnInfo.teamId, 
                    "dead": entity.contextualId in Kernel().battleFrame.deadFightersList,
                    "hidden": entity.contextualId in Kernel().fightContextFrame.hiddenEntites,
                    "summoned": entity.stats.summoned,
                    "canhit": canCast,
                    "cell": entity.disposition.cellId,
                    "id": entity.contextualId,
                    "reason": reason,
                    "hitpoints": f"{hp}",
                    "isMonster": ismonster
                }
                infosTable.append(entry)
                if (
                    entry["teamId"] != self.fighterInfos.spawnInfo.teamId
                    and not entry["dead"]
                    and not entry["hidden"]
                    and (targetSum or not entry["summoned"])
                    and entry["canhit"]
                    and entry["cell"] != -1
                ):
                    result.append(Target(entity, self.fighterInfos.disposition.cellId))
        headers = ["name", "id", "cell", "level", "hitpoints", "hidden", "summoned", "canhit", "reason"]
        format_row = f"{{:<20}} {{:<10}} {{:<10}} {{:<10}} {{:<10}} {{:<10}} {{:<10}} {{:<10}} {{:<30}}"
        row_delimiter = "-" * 120
        Logger().info(format_row.format(*headers))
        Logger().info(row_delimiter)
        for e in infosTable:
            Logger().info(format_row.format(*[e[h] for h in headers]))
        return result

    def playTurn(self):
        if not self.currentPlayer:
            Logger().warning(f"Play turn called withour defined currentPlayer")
        self._currentPath = None
        self._currentTarget = None
        Logger().info(f"[FightBot] Turn playing : {self.currentPlayer.name} ({self.currentPlayer.id}).")
        canCast, reason = self.canCastSpell()
        if not canCast:
            Logger().info(f"[FightBot] can no more cast spell for reason : {reason}")
            self.addTurnAction(self.turnEnd, [])
            self.nextTurnAction("play turn no targets")
            return
        
        targets = self.getTargetableEntities(self.spellw, targetSum=False)
        if not targets:
            targets = self.getTargetableEntities(self.spellw, targetSum=True)
            if not targets:
                self.addTurnAction(self.turnEnd, [])
                self.nextTurnAction("play turn no targets")
                return
        Logger().info(f"[FightBot] MP : {self.movementPoints}, AP : {self.actionPoints}.")
        Logger().info(f"[FightBot] Current attack spell : {self.spellw.spell.name}.")
        Logger().info(f"[FightBot] Current spell range : {self.getActualSpellRange(self.spellw)}.")
        Logger().info(f"[FightBot] Found targets : {[str(tgt) for tgt in targets]}.")
        target, path = self.findPathToTarget(self.spellw, targets)
        if path is not None:
            Logger().info(f"[FightBot] Found path {path} to target {target}.")
            self._currentTarget = target
            mpCount = 0
            mpLost = 0
            apLost = 0
            movementPoints = self.movementPoints
            actionPoints = self.actionPoints
            canHitTarget = target is not None
            if len(path) > 1:
                lastCellId = path[0]
                for cellId in path[1:]:
                    tackle = TackleUtil.getTackle(self.fighterInfos, MapPoint.fromCellId(lastCellId))
                    mpLost += int((self.movementPoints - mpCount) * (1 - tackle) + 0.5)
                    apLost += int(actionPoints * (1 - tackle) + 0.5)
                    if apLost < 0:
                        apLost = 0
                    if mpLost < 0:
                        mpLost = 0
                    movementPoints = self.movementPoints - mpLost
                    actionPoints = self.actionPoints - apLost
                    if mpCount < movementPoints:
                        mpCount += 1
                    else:
                        break
                    lastCellId = cellId
                canHitTarget = target and actionPoints >= self.spellw["apCost"] and mpCount >= len(path) - 1
                self._currentPath = path[:mpCount + 1]
                if len(self._currentPath) > 1:
                    self.addTurnAction(self.askMove, [self._currentPath])
            if canHitTarget:
                self.addTurnAction(self.castSpell, [self.spellId, target.pos.cellId])
            else:
                self.addTurnAction(self.turnEnd, [])
        else:
            Logger().info("[FightBot] No path found.")
            self.addTurnAction(self.turnEnd, [])
        self.nextTurnAction("play turn")

    def getActualSpellRange(self, spellw: SpellWrapper) -> int:
        range: int = spellw["range"]
        minRange: int = spellw["minRange"]
        if spellw["rangeCanBeBoosted"]:
            range += self.playerStats.getStatTotalValue(StatIds.RANGE) - self.playerStats.getStatAdditionalValue(
                StatIds.RANGE
            )
        range = max(min(max(minRange, range), AtouinConstants.MAP_WIDTH * AtouinConstants.MAP_HEIGHT), 0)
        return range

    def getSpellShape(self, spellw: SpellWrapper) -> int:
        if not self._spellShape:
            self._spellShape = 0
            spellEffect: EffectInstance = None
            for spellEffect in spellw["effects"]:
                if spellEffect.zoneShape != 0 and (
                    spellEffect.zoneSize > 0
                    or spellEffect.zoneSize == 0
                    and (spellEffect.zoneShape == SpellShapeEnum.P or spellEffect.zoneMinSize < 0)
                ):
                    self._spellShape = spellEffect.zoneShape
                    break
        return self._spellShape

    def getSpellZone(self, spellw: SpellWrapper) -> IZone:
        range = self.getActualSpellRange(spellw)
        minRange = spellw["minRange"]
        if range is None or minRange is None:
            raise Exception(f"Spell range is None, {minRange} {range}")
        spellShape = self.getSpellShape(spellw)
        castInLine = spellw["castInLine"] or (spellShape == SpellShapeEnum.l)
        if castInLine:
            if spellw["castInDiagonal"]:
                shapePlus = Cross(minRange, range, DataMapProvider())
                shapePlus.allDirections = True
                return shapePlus
            return Cross(minRange, range, DataMapProvider())
        elif spellw["castInDiagonal"]:
            shapePlus = Cross(minRange, range, DataMapProvider())
            shapePlus.diagonal = True
            return shapePlus
        else:
            return Lozenge(minRange, range, DataMapProvider())

    def addTurnAction(self, fct: FunctionType, args: list) -> None:
        self._turnAction.append({"fct": fct, "args": args})

    def nextTurnAction(self, event=None) -> None:
        if self._isRequestingMovement or self._requestingCastSpell or not self._myTurn:
            return
        if not Kernel().battleFrame:
            Logger().error("[FightAlgo] No battle frame found")
            return
        if Kernel().battleFrame._sequenceFrames or Kernel().battleFrame._executingSequence:
            Logger().warning(
                f"[FightAlgo] Waiting for {len(Kernel().battleFrame._sequenceFrames)} sequences to end, "
                    f"currently executing {Kernel().battleFrame._executingSequence} ..."
            )
            Kernel().battleFrame.logState()
            KernelEventsManager().once(KernelEvent.SEQUENCE_EXEC_FINISHED, self.nextTurnAction, originator=self)
            return
        if self.VERBOSE:
            Logger().info(f"[FightBot] Next turn actions, {[a['fct'].__name__ for a in self._turnAction]}")
        if self._turnAction:
            action = self._turnAction.pop(0)
            self._waitingSeqEnd = True
            action["fct"](*action["args"])
        else:
            self.playTurn()

    def updateReachableCells(self) -> None:
        self._reachableCells = FightReachableCellsMaker(self.fighterInfos).reachableCells

    def canCastSpell(self, targetId: int=0) -> bool:
        return CurrentPlayedFighterManager().canCastThisSpell(self.spellId, self.spellw.spellLevel, targetId)
            
    def onMemberJoinedFight(self, player: Character):
        if not ConnectionsHandler.getInstance(player.login) or not ConnectionsHandler.getInstance(player.login).inGameServer():
            Logger().warning(f"Member {player.name} is still disconnected waiting for him to conect ...")
            return BotEventsManager().onceMuleJoinedFightContext(player.id, lambda: self.onMemberJoinedFight(player), originator=self)
        PlayedCharacterManager.getInstance(player.login).isFighting = True
        if not self.fightResumed:
            startFightMsg = GameFightReadyMessage()
            startFightMsg.init(True)
            ConnectionsHandler.getInstance(player.login).send(startFightMsg)
            notjoined = [
                m.name for m in BotConfig().fightPartyMembers if not Kernel().fightEntitiesFrame.getEntityInfos(m.id)
            ]
            if not notjoined:
                Logger().info(f"[FightBot] All party members joined fight.")
                startFightMsg = GameFightReadyMessage()
                startFightMsg.init(True)
                ConnectionsHandler().send(startFightMsg)
                self.fightReadySent = True
    
    def process(self, msg: Message) -> bool:
        if isinstance(msg, GameFightOptionStateUpdateMessage):
            if msg.option not in BotConfig().fightOptions:
                BotConfig().fightOptions.append(msg.option)
            if Kernel().worker.getFrameByName("RoleplayEntitiesFrame"):
                return False
            return True

        elif isinstance(msg, GameFightJoinMessage):
            Logger().separator("Joined fight", "*")
            BotConfig().lastFightTime = perf_counter()
            self._fightCount += 1
            self._spellCastFails = 0
            self._inFight = True
            self.fightReadySent = False 
            if BotConfig().isLeader:
                if FightOptionsEnum.FIGHT_OPTION_SET_SECRET not in BotConfig().fightOptions:
                    gfotmsg = GameFightOptionToggleMessage()
                    gfotmsg.init(FightOptionsEnum.FIGHT_OPTION_SET_SECRET)
                    ConnectionsHandler().send(gfotmsg)
                if FightOptionsEnum.FIGHT_OPTION_SET_TO_PARTY_ONLY not in BotConfig().fightOptions:
                    gfotmsg = GameFightOptionToggleMessage()
                    gfotmsg.init(FightOptionsEnum.FIGHT_OPTION_SET_TO_PARTY_ONLY)
                    ConnectionsHandler().send(gfotmsg)
            return True

        elif isinstance(msg, GameFightEndMessage):
            self._inFight = False
            return True

        elif isinstance(msg, GameActionFightNoSpellCastMessage):
            if not self.currentPlayer:
                return
            Logger().error(f"[FightBot] Failed to cast spell")
            if self._requestingCastSpell:
                self._turnAction.clear()
                self._requestingCastSpell = False
                if self._spellCastFails > 2:
                    self.turnEnd()
                    return True
                self._spellCastFails += 1
                self.playTurn()
            return True

        elif isinstance(msg, GameMapNoMovementMessage):
            if not self.currentPlayer:
                return
            Logger().error(f"[FightBot] Failed to move")
            if self._isRequestingMovement and Kernel().turnFrame and Kernel().turnFrame.myTurn:
                self._turnAction.clear()
                self._isRequestingMovement = False
                if self._moveRequestFails > 2:
                    self.turnEnd()
                    return True
                self._moveRequestFails += 1
                self.playTurn()
            return True

        elif isinstance(msg, GameFightShowFighterMessage):
            if BotConfig().isLeader:
                fighterId = msg.informations.contextualId
                self._turnPlayed = 0
                self._myTurn = False
                player = BotConfig().getPlayerById(fighterId)
                if player:
                    if player.id != BotConfig().character.id:
                        Logger().info(f"[FightBot] Party member {player.name} joined fight.")
                        self.onMemberJoinedFight(player)
                    else:
                        Logger().info(f"[FightBot] Party Leader {player.name} joined fight.")
                elif fighterId > 0 and fighterId != BotConfig().character.id:
                    Logger().error(f"[FightBot] Unknown Player {fighterId} joined fight.")
                elif fighterId < 0:
                    Logger().info(f"[FightBot] Monster {fighterId} appeared.")
            return False

        elif isinstance(msg, SequenceEndMessage):
            if self._myTurn:
                if self._seqQueue:
                    self._seqQueue.pop()
                    if not self._seqQueue:
                        self._waitingSeqEnd = False
                        self.checkCanPlay()
            return True

        elif isinstance(msg, SequenceStartMessage):
            if self._myTurn:
                self._waitingSeqEnd = True
                self._seqQueue.append(msg)
            return True

        elif isinstance(msg, GameFightTurnStartMessage):
            if not Kernel().fightEntitiesFrame:
                return KernelEventsManager().onceFramePushed("FightEntitiesFrame", self.process, [msg], originator=self)
            Logger().separator(f"Player {msg.id} turn to play", "~")
            self._currentPlayerId = msg.id
            if not self._lastPlayerId:
                self._lastPlayerId = self._currentPlayerId
            if not isinstance(msg, GameFightTurnResumeMessage):
                BuffManager().decrementDuration(msg.id)
                BuffManager().resetTriggerCount(msg.id)
            if Kernel().battleFrame:
                Kernel().battleFrame.removeSavedPosition(msg.id)
                if Kernel().fightEntitiesFrame:
                    for entityId, infos in Kernel().fightEntitiesFrame.entities.items():
                        if infos and infos.stats.summoner == msg.id:
                            Kernel().battleFrame.removeSavedPosition(entityId)
            self.currentPlayer = BotConfig().getPlayerById(self._currentPlayerId)
            if self.currentPlayer:
                self.onPlayer()
            if self._turnStartPlaying:
                self.checkCanPlay()
            return True
        
        elif isinstance(msg, GameFightTurnEndMessage):
            if self._myTurn:
                self._isRequestingMovement = False
                self._requestingCastSpell
                self._lastPlayerId = msg.id
                self._myTurn = False
            return True

        elif isinstance(msg, GameFightTurnStartPlayingMessage):
            if self._myTurn:
                self.checkCanPlay()
            else:
                self._turnStartPlaying = True

        elif isinstance(msg, GameFightTurnReadyRequestMessage):
            if Kernel().battleFrame._executingSequence:
                Logger().warn("[FightBot] Delaying turn end acknowledgement because we're still in a sequence.")
                self._confirmTurnEnd = True
            else:
                self.confirmTurnEnd()
                self._turnStartPlaying = False
            return True

        elif isinstance(msg, MuleSwitchedToCombatContext):
            Logger().info(f"Mule {msg.muleId} in fight context")
            BotEventsManager().send(BotEventsManager.MULE_FIGHT_CONTEXT, msg.muleId)
            return True
        return False

    def onServerTextInfo(self, event, msgId, msgType, textId, text):
        if textId == 4993: # Wants to use more than the pms available
            self.turnEnd()
        if textId == 4897: # Something is blocking the way
            pass
        if textId == 144451: # An obstacle is blocking LOS
            self._requestingCastSpell = False
            self._turnAction.clear()
            self.turnEnd()
        return True

    @property
    def spellw(self) -> SpellWrapper:
        if not self.playerManager:
            Logger().error("Asking for spellw when there is no player manager")
            return None
        res = self.playerManager.getSpellById(self.spellId)
        if not res:
            Logger().error(f"Plyaer {self.currentPlayer.name} doesn't have spelllist {self.playerManager.playerSpellList}")
            res = SpellWrapper.create(self.spellId)
            spell = Spell.getSpellById(self.spellId)
            currentCharacterLevel = self.playerManager.limitedLevel
            spellLevels = spell.spellLevelsInfo
            index = 0
            for i in range(len(spellLevels) - 1, -1, -1):
                if currentCharacterLevel >= spellLevels[i].minPlayerLevel:
                    index = i
                    break
            res._spellLevel = spellLevels[index]
            res.spellLevel = index + 1
            self.playerManager.playerSpellList.append(res)
        return res
        
    def onPlayer(self) -> None:
        if not self.currentPlayer:
            return Logger().error(f"Something weird happend, called onPlayer when currrentPlayer is None")
        if not self.playerManager:
            Logger().warning(f"[FightBot] {self.currentPlayer.name} seems to be disconnected")
            return BotEventsManager().onceMuleJoinedFightContext(self.currentPlayer.id, lambda: self.onPlayer(), originator=self)
        Logger().info(f"[FightBot] It's {self.currentPlayer.name}'s turn to play")
        self._forbidenCells.clear()
        self._myTurn = True
        self.preparePlayableCharacter()
        self.checkCanPlay()
        self._turnPlayed += 1
        
    @property
    def actionPoints(self) -> int:
        stats = CurrentPlayedFighterManager().getStats()
        return stats.getStatTotalValue(StatIds.ACTION_POINTS)

    @property
    def movementPoints(self) -> int:
        stats = CurrentPlayedFighterManager().getStats()
        return stats.getStatTotalValue(StatIds.MOVEMENT_POINTS)

    def checkCanPlay(self):
        if not Kernel().turnFrame or not Kernel().turnFrame.myTurn or not self.currentPlayer or not self.playerManager:
            return
        if self._confirmTurnEnd:
            self.confirmTurnEnd()
            self._confirmTurnEnd = False
            return True
        if self._myTurn and not self._waitingSeqEnd:
            self.nextTurnAction("checkCanPlay")
                    
    def turnEnd(self) -> None:
        if self.currentPlayer is not None and self.connection is not None:
            self._spellCastFails = 0
            self._myTurn = False
            self._seqQueue.clear()
            self._turnAction.clear()
            gftfmsg = GameFightTurnFinishMessage()
            gftfmsg.init(False)
            if self.connection and self.connection.inGameServer():
                self.connection.send(gftfmsg)
            else:
                Logger().warning("Dropped turn end message coz player seems to be out of server game")

    @property
    def fighterInfos(self) -> "GameFightFighterInformations":
        return Kernel().fightEntitiesFrame.getEntityInfos(self.currentPlayer.id)

    @property
    def fighterPos(self) -> "MapPoint":
        return EntitiesManager().getEntity(self.currentPlayer.id).position

    def castSpell(self, spellId: int, cellId: bool) -> None:
        Logger().info(f"[FightBot] Casting spell {spellId} on cell {cellId}")
        if not self._requestingCastSpell:
            canCast, reason = self.canCastSpell(cellId)
            if canCast:
                line = MapTools.getMpLine(self.fighterPos.cellId, cellId)
                los = True
                if len(line) > 1:
                    for mp in line[:-1]:
                        if not DataMapProvider().pointLos(mp.x, mp.y, False):
                            los = False
                            break
                if not los:
                    Logger().warn(f"[FightBot] Can't cast spell {spellId} on cell {cellId} because of LOS")
                    self._turnAction.clear()
                    self._forbidenCells.add(cellId)
                    return self.nextTurnAction("from cast spell")
                self._requestingCastSpell = True
                BotEventsManager().onceFighterCastedSpell(self._currentPlayerId, cellId, self.onSpellCasted, originator=self)
                gafcrmsg = GameActionFightCastRequestMessage()
                gafcrmsg.init(spellId, cellId)
                self.connection.send(gafcrmsg)
            else:
                Logger().warning(f"Cant cast spell for reason : {reason}")

    def onSpellCasted(self) -> None:
        if self._requestingCastSpell:
            Logger().info(f"[FightBot] Spell casted.")
            self._requestingCastSpell = False
            self.checkCanPlay()

    def askMove(self, cells: list[int] = []) -> bool:
        self._isRequestingMovement = True
        path = MovementPath()
        path.fillFromCellIds(cells[:-1])
        path.end = MapPoint.fromCellId(cells[-1])
        path.path[-1].orientation = path.path[-1].step.orientationTo(path.end)
        Logger().info(f"[FightBot] Moving {path}.")
        gmmrmsg = GameMapMovementRequestMessage()
        keyMovements = path.keyMoves()
        currMapId = PlayedCharacterManager().currentMap.mapId
        gmmrmsg.init(keyMovements, currMapId)
        def onMovementApplied(movePath: MovementPath) -> None:
            if self._isRequestingMovement:
                Logger().info(f"[FightBot] Movement applied, landed on cell {self.fighterPos.cellId}.")
                self._isRequestingMovement = False
                if movePath.end.cellId != path.end.cellId:
                    Logger().warn(f"[FightBot] Movement failed to reach dest cell.")
                    stoppedOnCellIdx = cells.index(movePath.end.cellId)
                    if not stoppedOnCellIdx:
                        Logger().error(f"[FightBot] Couldnt find last reached cell in path.")
                    else:
                        unreachableCell = cells[stoppedOnCellIdx + 1]
                        Logger().warning(f"[FightBot] Cell {unreachableCell} is maybe unreachable")
                        entities = Kernel().fightEntitiesFrame.hasEntity(unreachableCell)
                        if entities:
                            Logger().warning(f"[FightBot] Entites {[e.id for e in entities]} are on cell {unreachableCell}")
                            self._forbidenCells.add(unreachableCell)
                        if unreachableCell in DataMapProvider().obstaclesCells:
                            Logger().warning(f"[FightBot] Cell {unreachableCell} is an obstacle")
                            self._forbidenCells.add(unreachableCell)
                        self._turnAction.clear()
                self.checkCanPlay()
        BotEventsManager().onceFighterMoved(self._currentPlayerId, onMovementApplied, originator=self)
        self.connection.send(gmmrmsg)
        self._lastMoveRequestTime = perf_counter()
        return True

    def confirmTurnEnd(self) -> None:
        if self.currentPlayer:
            fighterInfos = Kernel().fightEntitiesFrame.getEntityInfos(self.currentPlayer.id)
            if fighterInfos:
                BuffManager().markFinishingBuffs(self.currentPlayer.id)
                SpellWrapper.refreshAllPlayerSpellHolder(self.currentPlayer.id)
            else:
                Logger().error(f"[FightBot] Can't find fighter infos for player {self.currentPlayer.id}")
            spellCastManager = CurrentPlayedFighterManager().getSpellCastManagerById(self.currentPlayer.id)
            if spellCastManager:
                spellCastManager.nextTurn()
        self.currentPlayer = None
        turnEnd = GameFightTurnReadyMessage()
        turnEnd.init(True)
        ConnectionsHandler().send(turnEnd)

    def preparePlayableCharacter(self) -> None:            
        self._spellCastFails = False
        self._requestingCastSpell = False
        self._isRequestingMovement = False
        CurrentPlayedFighterManager().playerManager = PlayedCharacterManager.getInstance(self.currentPlayer.login)
        CurrentPlayedFighterManager().currentFighterId = self._currentPlayerId
        CurrentPlayedFighterManager.conn = self.connection
        CurrentPlayedFighterManager().resetPlayerSpellList()
        SpellWrapper.refreshAllPlayerSpellHolder(self._currentPlayerId)
        SpellInventoryManagementFrame().applySpellGlobalCoolDownInfo(self._currentPlayerId)
        CurrentPlayedFighterManager().playerManager.isFighting = True
        self._spellCastFails = 0
        self._moveRequestFails = 0
        self._seqQueue.clear()
        self._turnAction.clear()
        if Kernel().turnFrame:
            Kernel().turnFrame.myTurn = True
            
    def drawPath(self, cell:MapPoint = None) -> None:
        cells = list[int]()
        cellsTackled = list[int]()
        cellsUnreachable = list[int]()
        stats = StatsManager().getStats(self.playerManager.id)
        movementPoints = stats.getStatTotalValue(StatIds.MOVEMENT_POINTS)
        actionPoints = stats.getStatTotalValue(StatIds.ACTION_POINTS)
        path = Pathfinding().findPath(self.fighterPos, cell, False, False, True)
        firstObstacle = None
        if len(DataMapProvider().obstaclesCells) > 0 and (len(path) == 0 or len(path) > movementPoints):
            path = Pathfinding().findPath(self.fighterPos, cell, False, False, False)
            if len(path) > 0:
                for i in range(len(path)):
                    if path[i].cellId in DataMapProvider().obstaclesCells:
                        firstObstacle = path[i]
                        cellsUnreachable += [pe.cellId for pe in path.path[i + 1:]]
                        path.end = firstObstacle.step
                        path.path = path.path[:i]
        if len(path.path) == 0 or len(path.path) > movementPoints:
            return cells, cellsTackled, cellsUnreachable
        mpCount = 0
        mpLost = 0
        apLost = 0
        lastPe = path[0]
        for pe in path.path[1:]:
            tackle = TackleUtil.getTackle(self.fighterInfos, lastPe.step)
            mpLost += int((movementPoints - mpCount) * (1 - tackle) + 0.5)
            if mpLost < 0:
                mpLost = 0
            apLost += int(actionPoints * (1 - tackle) + 0.5)
            if apLost < 0:
                apLost = 0
            movementPoints = stats.getStatTotalValue(StatIds.MOVEMENT_POINTS) - mpLost
            actionPoints = stats.getStatTotalValue(StatIds.ACTION_POINTS) - apLost
            if mpCount < movementPoints:
                if mpLost > 0:
                    cellsTackled.append(pe.cellId)
                else:
                    cells.append(pe.cellId)
                mpCount += 1
            else:
                cellsUnreachable.append(pe.cellId)
            lastPe = pe
        tackle = TackleUtil.getTackle(self.fighterInfos, lastPe.step)
        mpLost += int((movementPoints - mpCount) * (1 - tackle) + 0.5)
        if mpLost < 0:
            mpLost = 0
        apLost += int(actionPoints * (1 - tackle) + 0.5)
        if apLost < 0:
            apLost = 0
        movementPoints = stats.getStatTotalValue(StatIds.MOVEMENT_POINTS) - mpLost
        if mpCount < movementPoints:
            if firstObstacle:
                movementPoints = len(path)
            if mpLost > 0:
                cellsTackled.append(path.end.cellId)
            else:
                cells.append(path.end.cellId)
        elif firstObstacle:
            cellsUnreachable.remove(path.end.cellId)
            movementPoints = len(path) - 1
        else:
            cellsUnreachable.append(path.end.cellId)
        return cells, cellsTackled, cellsUnreachable