from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.movement.AutoTripUseZaap import AutoTripUseZaap
from pyd2bot.logic.roleplay.behaviors.npc.NpcDialog import NpcDialog
from pyd2bot.misc.BotEventsmanager import BotEventsManager
from pydofus2.com.ankamagames.berilia.managers.EventsHandler import Listener
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEventsManager,
)
from pydofus2.com.ankamagames.dofus.internalDatacenter.quests.TreasureHuntStepWrapper import TreasureHuntStepWrapper
from pydofus2.com.ankamagames.dofus.internalDatacenter.quests.TreasureHuntWrapper import TreasureHuntWrapper
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.network.enums.TreasureHuntFlagStateEnum import TreasureHuntFlagStateEnum
from pydofus2.com.ankamagames.dofus.network.types.game.context.roleplay.party.PartyMemberInformations import (
    PartyMemberInformations,
)
from pydofus2.com.ankamagames.dofus.network.types.game.context.roleplay.treasureHunt.TreasureHuntStep import (
    TreasureHuntStep,
)
from pydofus2.com.ankamagames.dofus.network.types.game.context.roleplay.treasureHunt.TreasureHuntFlag import (
    TreasureHuntFlag,
)
from pydofus2.com.ankamagames.dofus.types.enums.TreasureHuntStepTypeEnum import TreasureHuntStepTypeEnum
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


class TreasureHunt(AbstractBehavior):
    def __init__(self) -> None:
        super().__init__()
        self.infos: TreasureHuntWrapper = None
        self.currentStep: TreasureHuntStepWrapper = None

    def run(self):
        # TODO: NpcDialog().start(callback=self.onTreasureHuntNPCDialogEnded, prent=self)
        pass

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
            AutoTripUseZaap().start(self.infos.stepList, callback=self.onStartMapReached, parent=self)
        elif self.currentStep.type == TreasureHuntStepTypeEnum.DIRECTION_TO_POI:
            self.currentStep.direction 
    
    def onStartMapReached(self, code, err):
        if err:
            self.finish(code, err)
        
