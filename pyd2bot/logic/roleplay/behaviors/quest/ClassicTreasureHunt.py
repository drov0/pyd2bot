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
from pydofus2.com.ankamagames.dofus.datacenter.quest.treasureHunt.PointOfInterest import \
    PointOfInterest
from pydofus2.com.ankamagames.dofus.datacenter.world.MapPosition import \
    MapPosition
from pydofus2.com.ankamagames.dofus.internalDatacenter.quests.TreasureHuntStepWrapper import \
    TreasureHuntStepWrapper
from pydofus2.com.ankamagames.dofus.internalDatacenter.quests.TreasureHuntWrapper import \
    TreasureHuntWrapper
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Vertex import \
    Vertex
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.WorldGraph import \
    WorldGraph
from pydofus2.com.ankamagames.dofus.network.enums.TreasureHuntFlagStateEnum import \
    TreasureHuntFlagStateEnum
from pydofus2.com.ankamagames.dofus.network.enums.TreasureHuntRequestEnum import \
    TreasureHuntRequestEnum
from pydofus2.com.ankamagames.dofus.network.enums.TreasureHuntTypeEnum import \
    TreasureHuntTypeEnum
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
MAP_POI_FILE = os.path.join(CURR_DIR, "map_poi.json")
with open(MAP_POI_FILE, "r") as fp:
    MAP_POI = json.load(fp)
DIRECTION_COORD = {
    DirectionsEnum.UP: (0, -1),
    DirectionsEnum.DOWN: (0, 1),
    DirectionsEnum.RIGHT: (1, 0),
    DirectionsEnum.LEFT: (-1, 0),
}


class ClassicTreasureHunt(AbstractBehavior):
    UNABLE_TO_FIND_NEXT_STEP = 475556

    TAKE_QUEST_MAPID = 128452097
    TREASURE_HUNT_ATM_IEID = 484993
    TREASURE_HUNT_ATM_SKILLUID = 152643320

    def __init__(self) -> None:
        super().__init__()
        self.infos: TreasureHuntWrapper = None
        self.currentStep: TreasureHuntStepWrapper = None

    def run(self):
        self.on(KernelEvent.TreasureHuntUpdate, self.onTreasureHuntUpdate)
        self.infos = Kernel().questFrame.getTreasureHunt(TreasureHuntTypeEnum.TREASURE_HUNT_CLASSIC)
        if self.infos is not None:
            return self.solveNextStep()
        self.autotripUseZaap(self.infos.stepList, callback=self.onTakeQuestMapReached)

    def onTakeQuestMapReached(self, code, err):
        if err:
            return self.finish(code, err)
        self.UseSkill(
            elementId=self.TREASURE_HUNT_ATM_IEID,
            skilluid=self.TREASURE_HUNT_ATM_SKILLUID,
            callback=self.onTreasurHuntTaken,
        )

    def onTreasurHuntTaken(self, code, err):
        if err:
            return self.finish(code, err)
        self.once(KernelEvent.TreasureHuntRequestAnswer, self.onTreaSureHuntRequestAnswer)

    def onTreaSureHuntRequestAnswer(self, event, answerType, err):
        if answerType == TreasureHuntRequestEnum.TREASURE_HUNT_OK:
            if not self.hasListener(KernelEvent.TreasureHuntUpdate):
                self.on(KernelEvent.TreasureHuntUpdate, self.onTreasureHuntUpdate)
        else:
            self.finish(answerType, err)

    @property
    def currentMap(self):
        return PlayedCharacterManager().currentMap.mapId

    @classmethod
    def getNextHintMap(cls, currMapId, poiId, direction):
        mapId = currMapId
        for i in range(10):
            mapId = cls.canChangeMap(mapId, direction)
            if not mapId:
                raise Exception("No map found in the given direction !!")
            Logger().debug(f"iter {i + 1}: nextMapId {mapId}, map pois {MAP_POI.get(str(int(mapId)), [])}")
            if poiId in MAP_POI.get(str(int(mapId)), []):
                print(
                    f"Found {PointOfInterest.getPointOfInterestById(poiId).name} in Map {mapId} {i + 1} maps to the {DirectionsEnum(direction)}"
                )
                return mapId
        return None

    @classmethod
    def canChangeMap(cls, mapId, direction):
        vertex = WorldGraph().getVertex(mapId, 1)
        for edge in WorldGraph().getOutgoingEdgesFromVertex(vertex):
            for transition in edge.transitions:
                if transition.direction != -1 and transition.direction == direction:
                    return edge.dst.mapId
        return None

    def solveNextStep(self):
        self.currentStep = self.infos.stepList[-1]        
        self.startMapId = self.infos.stepList[-2].mapId
        self.autotripUseZaap(self.startMapId, callback=self.onStartMapReached)

    def onNextHintMapReached(self, code, err):
        if err:
            return self.finish(code, err)
        Kernel().questFrame.treasureHuntFlagRequest(self.infos.questType, self.currentStep.index)

    def onTreasureHuntUpdate(self, questType: int):
        if questType == TreasureHuntTypeEnum.TREASURE_HUNT_CLASSIC:
            self.infos = Kernel().questFrame.getTreasureHunt(questType)
            self.solveNextStep()
        else:
            Logger().error(f"Unsupported treasure hunt type : {questType}")

    def onStartMapReached(self, code, err):
        if err:
            self.finish(code, err)
        if self.currentMap.type == TreasureHuntStepTypeEnum.FIGHT:
            Kernel().questFrame.treasureHuntDigRequest(self.infos.questType)
        elif self.currentStep.index == self.infos.totalStepCount - 1:
            Kernel().questFrame.treasureHuntDigRequest(self.infos.questType)
        elif self.currentStep.type == TreasureHuntStepTypeEnum.DIRECTION_TO_POI:
            Logger().debug(
                f"Current step : direction {DirectionsEnum(self.currentStep.direction)}, PoI : {PointOfInterest.getPointOfInterestById(self.currentStep.poiLabel)}"
            )
            nextMapId = self.getNextHintMap(self.currentMap, self.currentStep.poiLabel, self.currentStep.direction)
            self.autotripUseZaap(nextMapId, callback=self.onNextHintMapReached)
        else:
            raise Exception(f"Unsupported hunt step type {self.currentStep.type}")
        
if __name__ == "__main__":
    mapId = ClassicTreasureHunt.getNextHintMap(90701824.0, 879, 0)
    print(mapId)
