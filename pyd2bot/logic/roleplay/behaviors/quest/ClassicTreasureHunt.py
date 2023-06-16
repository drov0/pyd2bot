import json
import os

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.quest.FindHintNpc import FindHintNpc
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.dofus.datacenter.npcs.Npc import Npc
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
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.WorldGraph import \
    WorldGraph
from pydofus2.com.ankamagames.dofus.network.enums.TreasureHuntFlagStateEnum import \
    TreasureHuntFlagStateEnum
from pydofus2.com.ankamagames.dofus.network.enums.TreasureHuntRequestEnum import \
    TreasureHuntRequestEnum
from pydofus2.com.ankamagames.dofus.network.enums.TreasureHuntTypeEnum import \
    TreasureHuntTypeEnum
from pydofus2.com.ankamagames.dofus.types.enums.TreasureHuntStepTypeEnum import \
    TreasureHuntStepTypeEnum
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.types.enums.DirectionsEnum import \
    DirectionsEnum

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
HINTS_FILE = os.path.join(CURR_DIR, "hints.json")
DIRECTION_COORD = {
    DirectionsEnum.UP: (0, -1),
    DirectionsEnum.DOWN: (0, 1),
    DirectionsEnum.RIGHT: (1, 0),
    DirectionsEnum.LEFT: (-1, 0),
}


class ClassicTreasureHunt(AbstractBehavior):
    UNABLE_TO_FIND_HINT = 475556
    UNSUPPORTED_THUNT_TYPE = 475557

    TAKE_QUEST_MAPID = 128452097
    TREASURE_HUNT_ATM_IEID = 484993
    TREASURE_HUNT_ATM_SKILLUID = 152643320
    with open(HINTS_FILE, "r") as fp:
        hint_db = json.load(fp)

    def __init__(self) -> None:
        super().__init__()
        self.infos: TreasureHuntWrapper = None
        self.currentStep: TreasureHuntStepWrapper = None

    def getCurrentStepIndex(self):
        i = 1
        while i < len(self.infos.stepList):
            if self.infos.stepList[i].flagState == -1:
                return i
            i += 1
        return None

    def run(self):
        self.on(KernelEvent.TreasureHuntUpdate, self.onTreasureHuntUpdate)
        self.on(KernelEvent.TreasureHuntFinished, self.onTreasureHuntFinished)
        self.infos = Kernel().questFrame.getTreasureHunt(TreasureHuntTypeEnum.TREASURE_HUNT_CLASSIC)
        if self.infos is not None:
            return self.solveNextStep()
        Logger().debug(f"AutoTravelling to treasure hunt distributor")
        self.autotripUseZaap(self.TAKE_QUEST_MAPID, callback=self.onTakeQuestMapReached)

    def onTreasureHuntFinished(self, event, questType):
        if not Kernel().roleplayContextFrame:
            return KernelEventsManager().onceFramePushed(
                "RoleplayContextFrame", lambda: self.onTreasureHuntFinished(event, questType)
            )
        if not PlayedCharacterManager().currVertex:
            return KernelEventsManager().onceMapProcessed(lambda: self.onTreasureHuntFinished(event, questType))
        self.autotripUseZaap(self.TAKE_QUEST_MAPID, callback=self.onTakeQuestMapReached)

    def onTakeQuestMapReached(self, code, err):
        if err:
            return self.finish(code, err)
        Logger().debug(f"Getting treasure hunt from distributor")
        self.useSkill(
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
            Logger().debug(f"Treasure hunt accepted")
            if not self.hasListener(KernelEvent.TreasureHuntUpdate):
                self.on(KernelEvent.TreasureHuntUpdate, self.onTreasureHuntUpdate)
        else:
            self.finish(answerType, err)

    @property
    def currentMap(self):
        return PlayedCharacterManager().currentMap.mapId

    @classmethod
    def isPoiInMap(cls, mapId, poiId):
        mp = MapPosition.getMapPositionById(mapId)
        if str(mp.worldMap) not in cls.hint_db:
            return False
        worldHints = cls.hint_db[str(mp.worldMap)]
        if str(mp.id) not in worldHints:
            return False
        mapHints: list = worldHints[str(mp.id)]
        return poiId in mapHints

    def getNextHintMap(self):
        mapId = self.currentMap
        for i in range(10):
            mapId = self.nextMapInDirection(mapId, self.currentStep.direction)
            if not mapId:
                raise Exception("No map found in the given direction !!")
            Logger().debug(f"iter {i + 1}: nextMapId {mapId}.")

            if self.currentStep.type == TreasureHuntStepTypeEnum.DIRECTION_TO_POI and self.isPoiInMap(
                mapId, self.currentStep.poiLabel
            ):
                poi = PointOfInterest.getPointOfInterestById(self.currentStep.poiLabel)
                Logger().debug(
                    f"Found {poi.name} in Map {mapId} at {i + 1} maps to the {DirectionsEnum(self.currentStep.direction)}"
                )
                return mapId
        return None

    @classmethod
    def nextMapInDirection(cls, mapId, direction):
        for vertex in WorldGraph().getVertices(mapId).values():
            for edge in WorldGraph().getOutgoingEdgesFromVertex(vertex):
                for transition in edge.transitions:
                    if transition.direction != -1 and transition.direction == direction:
                        return edge.dst.mapId

    def solveNextStep(self):
        lastStep = self.currentStep
        idx = self.getCurrentStepIndex()
        if idx is None:
            self.currentStep = None
        else:
            self.currentStep = self.infos.stepList[idx]
            if lastStep == self.currentStep:
                raise Exception("Step didnt change!")
            self.startMapId = self.infos.stepList[idx - 1].mapId
        Logger().debug(f"Infos:\n{self.infos}")
        Logger().debug(f"AutoTravelling to treasure hunt step {idx}, start map {self.startMapId}")
        self.autotripUseZaap(self.startMapId, callback=self.onStartMapReached)

    def onNextHintMapReached(self, code, err):
        if err:
            return self.finish(code, err)
        Kernel().questFrame.treasureHuntFlagRequest(self.infos.questType, self.currentStep.index)

    def onTreasureHuntUpdate(self, event, questType: int):
        if questType == TreasureHuntTypeEnum.TREASURE_HUNT_CLASSIC:
            self.infos = Kernel().questFrame.getTreasureHunt(questType)
            self.solveNextStep()
        else:
            return self.finish(f"Unsupported treasure hunt type : {questType}")

    def onStartMapReached(self, code, err):
        if err:
            return self.finish(code, err)
        if self.currentStep is None:
            Kernel().questFrame.treasureHuntDigRequest(self.infos.questType)
        elif self.currentStep.type == TreasureHuntStepTypeEnum.FIGHT:
            Kernel().questFrame.treasureHuntDigRequest(self.infos.questType)
        elif self.currentStep.type == TreasureHuntStepTypeEnum.DIRECTION_TO_POI:
            Logger().debug(
                f"Current step : direction {self.currentStep}"
            )
            nextMapId = self.getNextHintMap()
            if not nextMapId:
                mp = MapPosition.getMapPositionById(self.currentMap)
                return self.finish(
                    self.UNABLE_TO_FIND_HINT,
                    f"Unable to find Map of poi {self.currentStep.poiLabel} from start map {self.currentMap}:({mp.posX}, {mp.posY})!",
                )
            self.autotripUseZaap(nextMapId, callback=self.onNextHintMapReached)
        elif self.currentStep.type == TreasureHuntStepTypeEnum.DIRECTION_TO_HINT:
            FindHintNpc().start(self.currentStep.count, self.currentStep.direction, parent=self, callback=self.onNextHintMapReached)
        else:
            return self.finish(self.UNSUPPORTED_THUNT_TYPE, f"Unsupported hunt step type {self.currentStep.type}")

        