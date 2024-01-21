import json
import random
import threading

from pyd2bot.logic.managers.BotConfig import BotConfig
from pydofus2.com.ankamagames.atouin.Haapi import Haapi
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import KernelEventsManager
from pydofus2.com.ankamagames.dofus.datacenter.breeds.Breed import Breed
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import ConnectionsHandler
from pydofus2.com.ankamagames.dofus.logic.common.managers.PlayerManager import PlayerManager
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.network.messages.game.achievement.AchievementRewardRequestMessage import (
    AchievementRewardRequestMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.stats.StatsUpgradeRequestMessage import (
    StatsUpgradeRequestMessage,
)
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.messages.Frame import Frame
from pydofus2.com.ankamagames.jerakine.messages.Message import Message
from pydofus2.com.ankamagames.jerakine.types.enums.Priority import Priority
from pydofus2.damageCalculation.tools.StatIds import StatIds


class BotCharacterUpdatesFrame(Frame):
    def __init__(self):
        super().__init__()

    def pushed(self) -> bool:
        KernelEventsManager().on(KernelEvent.PlayerLeveledUp, self.onBotLevelUp)
        KernelEventsManager().on(KernelEvent.CharacterStats, self.onBotStats)
        KernelEventsManager().on(KernelEvent.AchievementFinished, self.onAchievementFinished)
        KernelEventsManager().on(KernelEvent.ObtainedItem, self.onItemObtained)
        KernelEventsManager().on(KernelEvent.MapDataProcessed, self.onMapDataProcessed)
        self.waitingForCharactsBoost = threading.Event()
        return True

    def pulled(self) -> bool:
        KernelEventsManager().clearAllByOrigin(self)
        return True

    @property
    def priority(self) -> int:
        return Priority.VERY_LOW

    def getEventData(self, button_id, button_name):
        return json.dumps({
            "character_level": PlayedCharacterManager().limitedLevel,
            "button_id": button_id,
            "button_name": button_name,
            "server_id": PlayerManager().server.id,
            "character_id": PlayedCharacterManager().id,
            "account_id": PlayerManager().accountId,
        })
        
    def onItemObtained(self, event, iw, qty):
        if random.random() < 0.1:
            data = self.getEventData(3, "Inventory")
            Haapi().send_event(1, Haapi()._session_id, 730, data)
        elif random.random() < 0.1:
            data = self.getEventData(6, "Social")
            Haapi().send_event(1, Haapi()._session_id, 730, data)
        elif random.random() < 0.1:
            data = self.getEventData(4, "Quests")
            Haapi().send_event(1, Haapi()._session_id, 730, data)
            
    def onMapDataProcessed(self, event, map):
        if random.random() < 0.1:
            data = self.getEventData(5, "World Map")
            Haapi().send_event(1, Haapi()._session_id, 730, data)
    
    def onBotStats(self, event):
        unusedStatPoints = PlayedCharacterManager().stats.getStatBaseValue(StatIds.STATS_POINTS)
        if unusedStatPoints > 0 and not self.waitingForCharactsBoost.is_set():
            boost, usedCapital = self.getBoost(unusedStatPoints)
            if boost > 0:
                Logger().info(f"can boost point with {boost}")
                data = self.getEventData(1, "Characteristics")
                Haapi().send_event(1, Haapi()._session_id, 730, data)
                self.waitingForCharactsBoost.set()
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
                currentCost = (
                    statFloors[idxCurrFloor][1]
                    if idxCurrFloor < len(statFloors)
                    else statFloors[len(statFloors) - 1][0]
                )
        return boost, usedCapital

    def boostCharacs(self, boost, statId):
        rpeframe = Kernel().roleplayEntitiesFrame
        if not rpeframe or not rpeframe.mcidm_processed:
            return KernelEventsManager().onceMapProcessed(self.boostCharacs, [boost, statId], originator=self)
        sumsg = StatsUpgradeRequestMessage()
        sumsg.init(False, statId, boost)
        ConnectionsHandler().send(sumsg)
        KernelEventsManager().once(KernelEvent.StatsUpgradeResult, self.onStatUpgradeResult, originator=self)

    def onStatUpgradeResult(self, event, result, boost):
        self.waitingForCharactsBoost.clear()

    def process(self, msg: Message) -> bool:
        pass

    def onAchievementFinished(self, event, achievementId, finishedlevel):
        arrmsg = AchievementRewardRequestMessage()
        arrmsg.init(achievementId)
        ConnectionsHandler().send(arrmsg)
        return True
