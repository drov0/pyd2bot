from pydofus2.com.ankamagames.dofus.datacenter.breeds.Breed import Breed
import pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler as connh
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.network.messages.game.achievement.AchievementFinishedMessage import (
    AchievementFinishedMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.achievement.AchievementRewardRequestMessage import (
    AchievementRewardRequestMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.character.stats.CharacterLevelUpMessage import CharacterLevelUpMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.character.stats.CharacterStatsListMessage import (
    CharacterStatsListMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.stats.StatsUpgradeRequestMessage import (
    StatsUpgradeRequestMessage,
)
from pydofus2.com.ankamagames.jerakine.messages.Frame import Frame
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.messages.Message import Message
from pydofus2.com.ankamagames.jerakine.types.enums.Priority import Priority
from pydofus2.damageCalculation.tools.StatIds import StatIds
from pyd2bot.logic.managers.BotConfig import BotConfig

logger = Logger()


class BotCharacterUpdatesFrame(Frame):
    def __init__(self):
        self._myTurn = False
        self._statsInitialized = False
        super().__init__()

    def pushed(self) -> bool:
        return True

    def pulled(self) -> bool:
        return True

    @property
    def priority(self) -> int:
        return Priority.VERY_LOW

    @property
    def boostStat(self, statId: int, points: int):
        breed = Breed.getBreedById(PlayedCharacterManager().infos.breed)
        if statId == StatIds.STRENGTH:
            statFloors = breed.statsPointsForStrength
        elif statId == StatIds.VITALITY:
            statFloors = breed.statsPointsForVitality
        elif statId == StatIds.WISDOM:
            statFloors = breed.statsPointsForWisdom
        elif statId == StatIds.INTELLIGENCE:
            statFloors = breed.statsPointsForIntelligence
        elif statId == StatIds.AGILITY:
            statFloors = breed.statsPointsForAgility
        elif statId == StatIds.CHANCE:
            statFloors = breed.statsPointsForChance
        additional = PlayedCharacterManager().stats.getStatAdditionalValue(statId)
        base = PlayedCharacterManager().stats.getStatBaseValue(statId)
        logger.debug(f"Have {points} unused stat points")
        logger.debug(f"Stat {statId} has base {base} and additional {additional} so totoal = {base + additional}")
        currentStatPoints = base + additional
        for i in range(len(statFloors) + 1):
            if i + 1 == len(statFloors):
                nextFloor = float("inf")
            else:
                nextFloor = statFloors[i + 1][0]
            if statFloors[i][0] <= currentStatPoints < nextFloor:
                currentFloorCost = statFloors[i][1]
                break
        logger.debug(f"Current floor cost is {currentFloorCost}")
        boost = 0
        currPoints = points
        while True:
            nextFloor = statFloors[i + 1][0] if i + 1 < len(statFloors) else float("inf")
            ptsToInvest = min(currPoints, nextFloor - currentStatPoints)
            additionalBoost = ptsToInvest // currentFloorCost
            if additionalBoost == 0:
                break
            boost += additionalBoost
            currPoints -= additionalBoost * currentFloorCost
            currentFloorCost = statFloors[i + 1][1] if i + 1 < len(statFloors) else 4
            i += 1
        canUse = points - currPoints
        if boost > 0:
            logger.debug(f"Boosting {statId} by {canUse}")
            sumsg = StatsUpgradeRequestMessage()
            sumsg.init(False, statId, canUse)
            connh.ConnectionsHandler().conn.send(sumsg)

    def process(self, msg: Message) -> bool:

        if isinstance(msg, AchievementFinishedMessage):
            msg.achievement.id
            arrmsg = AchievementRewardRequestMessage()
            arrmsg.init(msg.achievement.id)
            connh.ConnectionsHandler().conn.send(arrmsg)
            return False

        elif isinstance(msg, CharacterLevelUpMessage):
            clumsg = msg
            if BotConfig().character["primaryStatId"]:
                previousLevel = PlayedCharacterManager().infos.level
                PlayedCharacterManager().infos.level = clumsg.newLevel
                pointsEarned = (clumsg.newLevel - previousLevel) * 5
                self.boostStat(BotConfig().character["primaryStatId"], pointsEarned)
            return True

        elif isinstance(msg, CharacterStatsListMessage):
            if not self._statsInitialized:
                unusedStatPoints = PlayedCharacterManager().stats.getStatBaseValue(StatIds.STATS_POINTS)
                if unusedStatPoints > 0:
                    self.boostStat(BotConfig().character["primaryStatId"], unusedStatPoints)
                self._statsInitialized = True
            return True
