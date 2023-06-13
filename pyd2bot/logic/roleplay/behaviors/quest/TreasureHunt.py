import json
import os

from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.npc.NpcDialog import NpcDialog
from pyd2bot.misc.BotEventsmanager import BotEventsManager
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.berilia.managers.Listener import Listener
from pydofus2.com.ankamagames.dofus.datacenter.world.MapPosition import \
    MapPosition
from pydofus2.com.ankamagames.dofus.internalDatacenter.quests.TreasureHuntStepWrapper import \
    TreasureHuntStepWrapper
from pydofus2.com.ankamagames.dofus.internalDatacenter.quests.TreasureHuntWrapper import \
    TreasureHuntWrapper
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.WorldGraph import \
    WorldGraph
from pydofus2.com.ankamagames.dofus.network.enums.TreasureHuntFlagStateEnum import \
    TreasureHuntFlagStateEnum
from pydofus2.com.ankamagames.dofus.network.enums.TreasureHuntRequestEnum import \
    TreasureHuntRequestEnum
from pydofus2.com.ankamagames.dofus.network.types.game.context.roleplay.party.PartyMemberInformations import \
    PartyMemberInformations
from pydofus2.com.ankamagames.dofus.network.types.game.context.roleplay.treasureHunt.TreasureHuntFlag import \
    TreasureHuntFlag
from pydofus2.com.ankamagames.dofus.network.types.game.context.roleplay.treasureHunt.TreasureHuntStep import \
    TreasureHuntStep
from pydofus2.com.ankamagames.dofus.types.enums.TreasureHuntStepTypeEnum import \
    TreasureHuntStepTypeEnum
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.types.enums.DirectionsEnum import \
    DirectionsEnum

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
with open(CURR_DIR, "r") as fp:
    MAP_POI = json.load(fp)
DIRECTION_COORD = {
    DirectionsEnum.UP: (0, -1),
    DirectionsEnum.DOWN: (0, 1),
    DirectionsEnum.RIGHT: (1, 0),
    DirectionsEnum.LEFT: (-1, 0),
}

class TreasureHunt(AbstractBehavior):
    TAKE_QUEST_MAPID = 128452097
    TREASURE_HUNT_ATM_IEID = 484993
    TREASURE_HUNT_ATM_SKILLUID = 152643320

    def __init__(self) -> None:
        super().__init__()
        self.infos: TreasureHuntWrapper = None
        self.currentStep: TreasureHuntStepWrapper = None

    def run(self):
        self.autotripUseZaap(self.infos.stepList, callback=self.onTakeQuestMapReached)
        self.on(KernelEvent.TreasureHuntUpdate, self.onTreasureHuntUpdate)
        
    def onTakeQuestMapReached(self, code, err):
        if err:
            return self.finish(code, err)
        self.UseSkill(elementId=self.TREASURE_HUNT_ATM_IEID, skilluid=self.TREASURE_HUNT_ATM_SKILLUID, callback=self.onTreasurHuntTaken)
    
    def onTreasurHuntTaken(self, code, err):
        if err:
            return self.finish(code, err)
        self.on(KernelEvent.TreasureHuntRequestAnswer, self.onTreaSureHuntRequestAnswer)
    
    def onTreaSureHuntRequestAnswer(self, event, answerType, err):
        if answerType == TreasureHuntRequestEnum.TREASURE_HUNT_ERROR_ALREADY_HAVE_QUEST:
            pass
        elif answerType == TreasureHuntRequestEnum.TREASURE_HUNT_ERROR_NO_QUEST_FOUND:
            pass
        elif answerType == TreasureHuntRequestEnum.TREASURE_HUNT_ERROR_UNDEFINED:
            pass
        elif answerType == TreasureHuntRequestEnum.TREASURE_HUNT_ERROR_NOT_AVAILABLE:
            pass
        elif answerType == TreasureHuntRequestEnum.TREASURE_HUNT_ERROR_DAILY_LIMIT_EXCEEDED:
            pass
        elif answerType == TreasureHuntRequestEnum.TREASURE_HUNT_OK:
            pass

    def getNextHintMap(self, poiId, direction):
        mapId = PlayedCharacterManager().currentMap.mapId
        for _ in range(10):
            nextMp = self.nextMapDirection(mapId, direction)
            if poiId in MAP_POI[nextMp.id]:
                return nextMp
        return None
    
    def nextMapDirection(self, mapId, direction):        
        if not self.canChangeMap(mapId, direction):
            Logger().debug(
                f"!!! can't change map from {currMp.id} to the {direction}"
            )
            return None
        currMp = MapPosition.getMapPositionById(mapId)
        dx, dy = DIRECTION_COORD[direction]
        nextCoord = (currMp.posX + dx, currMp.posY + dy)
        return MapPosition.getMapIdByCoord(*nextCoord)
    
    def canChangeMap(self, mapId, direction):
        if not WorldGraph().getVertices(mapId):
            return False
        for vertex in WorldGraph().getVertices(mapId).values():
            for edge in WorldGraph().getOutgoingEdgesFromVertex(vertex):
                for transition in edge.transitions:
                    if (
                        transition.direction
                        and DirectionsEnum(transition.direction) == direction
                    ):
                        return True
        return False
    
    def onTreasureHuntUpdate(self, questType: int):
        self.infos = Kernel().questFrame.getTreasureHunt(questType)
        self.currentStep = None
        for step in self.infos.stepList:
            if step.flagState != TreasureHuntFlagStateEnum.TREASURE_HUNT_FLAG_STATE_OK:
                self.currentStep = step
                break
        if self.currentStep is None:
            raise Exception("Couldn't find current step, all steps are either wrong or completed!")
        if self.currentStep.type == TreasureHuntStepTypeEnum.START:
            self.autotripUseZaap(self.infos.stepList, callback=self.onStartMapReached)
        elif self.currentStep.type == TreasureHuntStepTypeEnum.DIRECTION_TO_POI:
            Logger().debug(DirectionsEnum(self.currentStep.direction ))
    
    def onStartMapReached(self, code, err):
        if err:
            self.finish(code, err)
        
