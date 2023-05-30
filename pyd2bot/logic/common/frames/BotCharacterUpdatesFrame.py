from typing import TYPE_CHECKING

from pyd2bot.logic.managers.BotConfig import BotConfig
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.datacenter.breeds.Breed import Breed
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.network.messages.game.achievement.AchievementFinishedMessage import \
    AchievementFinishedMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.achievement.AchievementRewardRequestMessage import \
    AchievementRewardRequestMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.stats.StatsUpgradeRequestMessage import \
    StatsUpgradeRequestMessage
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.messages.Frame import Frame
from pydofus2.com.ankamagames.jerakine.messages.Message import Message
from pydofus2.com.ankamagames.jerakine.types.enums.Priority import Priority
from pydofus2.damageCalculation.tools.StatIds import StatIds

if TYPE_CHECKING:
    from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayEntitiesFrame import \
        RoleplayEntitiesFrame

class BotCharacterUpdatesFrame(Frame):
    def __init__(self):
        super().__init__()

    def pushed(self) -> bool:
        KernelEventsManager().on(KernelEvent.LEVEL_UP, self.onBotLevelUp)
        KernelEventsManager().on(KernelEvent.CHARACTER_STATS, self.onBotStats)
        return True

    def pulled(self) -> bool:
        KernelEventsManager().clearAllByOrigin(self)
        return True

    @property
    def priority(self) -> int:
        return Priority.VERY_LOW

    def onBotStats(self, event):
        unusedStatPoints = PlayedCharacterManager().stats.getStatBaseValue(StatIds.STATS_POINTS)
        if unusedStatPoints > 0:
            boost, usedCapital = self.getBoost(unusedStatPoints)
            if boost > 0:
                Logger().info(f"can boost point with {boost}")
                self.boostCharacs(usedCapital, BotConfig().primaryStatId)

    def onBotLevelUp(self, event, previousLevel, newLevel):
        pass

    def getStatFloor(self, statId: int):
        breed = Breed.getBreedById(PlayedCharacterManager().infos.breed)
        statFloors = {
            StatIds.STRENGTH: breed.statsPointsForStrength,
            StatIds.VITALITY: breed.statsPointsForVitality,
            StatIds.WISDOM: breed.statsPointsForWisdom,
            StatIds.INTELLIGENCE: breed.statsPointsForIntelligence,
            StatIds.AGILITY: breed.statsPointsForAgility,
            StatIds.CHANCE: breed.statsPointsForChance,
        }
        return statFloors[statId]

    def getCurrCost(self, x, statFloors):
        currCost = None
        currFloorIdx = None
        for idx, interval in enumerate(statFloors):
            start, cost = interval
            if start <= x:
                currCost = cost
                currFloorIdx = idx
            else:
                break
        return currFloorIdx, currCost

    def getBoost(self, capital):
        statId = BotConfig().primaryStatId
        statFloors = self.getStatFloor(statId)
        additional = PlayedCharacterManager().stats.getStatAdditionalValue(statId)
        base = PlayedCharacterManager().stats.getStatBaseValue(statId)
        currentBase = base + additional
        idxCurrFloor, currentCost = self.getCurrCost(currentBase, statFloors)
        boost = 0
        usedCapital = 0
        while True:
            nextFloor = statFloors[idxCurrFloor + 1][0] if idxCurrFloor + 1 < len(statFloors) else float("inf")
            capitalUntilNextFloor = (nextFloor - currentBase) * currentCost
            if capital <= capitalUntilNextFloor:
                boost += capital // currentCost
                usedCapital += currentCost * (capital // currentCost)
                break
            else:
                usedCapital += capitalUntilNextFloor
                boost += nextFloor - currentBase
                currentBase = nextFloor
                capital -= capitalUntilNextFloor
                idxCurrFloor += 1
                currentCost = statFloors[idxCurrFloor][1] if idxCurrFloor < len(statFloors) else statFloors[len(statFloors) - 1][0]
        return boost, usedCapital
    
    def boostCharacs(self, boost, statId):
        rpeframe: "RoleplayEntitiesFrame" = Kernel().worker.getFrameByName("RoleplayEntitiesFrame")
        if not rpeframe or not rpeframe.mcidm_processed:
            return KernelEventsManager().onceMapProcessed(self.boostCharacs, [boost, statId], originator=self)
        sumsg = StatsUpgradeRequestMessage()
        sumsg.init(False, statId, boost)
        ConnectionsHandler().send(sumsg)

    def process(self, msg: Message) -> bool:

        if isinstance(msg, AchievementFinishedMessage):
            msg.achievement.id
            arrmsg = AchievementRewardRequestMessage()
            arrmsg.init(msg.achievement.id)
            ConnectionsHandler().send(arrmsg)
            return True


