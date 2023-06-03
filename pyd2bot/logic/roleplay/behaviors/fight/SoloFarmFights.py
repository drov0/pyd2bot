import heapq

from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.AbstractFarmBehavior import \
    AbstractFarmBehavior
from pyd2bot.logic.roleplay.behaviors.fight.AttackMonsters import \
    AttackMonsters
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.dofus.datacenter.monsters.Monster import Monster
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.network.types.game.context.roleplay.GameRolePlayGroupMonsterInformations import \
    GameRolePlayGroupMonsterInformations
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.types.positions.MapPoint import MapPoint


class SoloFarmFights(AbstractFarmBehavior):

    def __init__(self, timeout):
        super().__init__(timeout)
    
    def init(self):
        self.path = BotConfig().path
        Logger().debug(f"Solo farm fights started")

    def getResourcesTableHeaders(self) -> list[str]:
        return ["mainMonsterName", "id", "cell", "distance"]

    def iterResourceToCollect(self):
        if not Kernel().entitiesFrame._monstersIds:
            return []
        availableMonsterFights = []
        visited = set()
        queue = list[int, MapPoint]()
        currCellId = PlayedCharacterManager().currentCellId
        teamLvl = sum(PlayedCharacterManager.getInstance(c.login).limitedLevel for c in BotConfig().fightPartyMembers)
        monsterByCellId = dict[int, GameRolePlayGroupMonsterInformations]()
        for entityId in Kernel().entitiesFrame._monstersIds:
            infos: GameRolePlayGroupMonsterInformations = Kernel().entitiesFrame.getEntityInfos(entityId)
            if infos:
                totalGrpLvl = infos.staticInfos.mainCreatureLightInfos.level + sum(
                    ul.level for ul in infos.staticInfos.underlings
                )
                if totalGrpLvl < BotConfig().monsterLvlCoefDiff * teamLvl:
                    monsterByCellId[infos.disposition.cellId] = infos
        if not monsterByCellId:
            return []
        heapq.heappush(queue, (0, currCellId))
        while queue:
            distance, currCellId = heapq.heappop(queue)
            if currCellId in visited:
                continue
            visited.add(currCellId)
            if currCellId in monsterByCellId:
                infos = monsterByCellId[currCellId]
                mainMonster = Monster.getMonsterById(infos.staticInfos.mainCreatureLightInfos.genericId)
                availableMonsterFights.append({
                    "mainMonsterName": mainMonster.name,
                    "id": infos.contextualId,
                    "cell": currCellId,
                    "distance": distance
                })
            for x, y in MapPoint.fromCellId(currCellId).iterChilds():
                adjacentPos = MapPoint.fromCoords(x, y)
                if adjacentPos.cellId in visited:
                    continue
                heapq.heappush(queue, (distance + 1, adjacentPos.cellId))
        Logger().debug(self.getAvailableResourcesTable(availableMonsterFights))
        availableMonsterFights.sort(key=lambda r : r['distance'])
        for r in availableMonsterFights:
            yield r
        
    def onFightStarted(self, code, error):        
        if not self.running.is_set():
            return
        if error:
            Logger().warning(error)
            if code == AttackMonsters.MAP_CHANGED:
                self.availableResources = None
                self.doFarm()
            elif code in [AttackMonsters.ENTITY_VANISHED, AttackMonsters.FIGHT_REQ_TIMEDOUT]:
                self.doFarm()
            else:
                return KernelEventsManager().send(KernelEvent.RESTART, f"Error while attacking monsters: {error}")

    def collectCurrResource(self):
        AttackMonsters().start(self.currentTarget["id"], callback=self.onFightStarted, parent=self)
