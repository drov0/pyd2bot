from typing import TYPE_CHECKING

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.npc.NpcDialog import NpcDialog
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.berilia.managers.Listener import Listener
from pydofus2.com.ankamagames.dofus.datacenter.world.SubArea import SubArea
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

if TYPE_CHECKING:
    pass


class GetOutOfAnkarnam(AbstractBehavior):
    ASTRUB_MAPLOAD_TIMEOUT = 20203
    npcId = -20001
    npcMapId = 153880835
    openGoToAstrubActionId = 3
    iAmSureReplyId = 36980
    goToAstrubReplyId = 36982
    ankarnamAreaId = 45
    astrubLandingMapId = 192416776

    def __init__(self) -> None:
        super().__init__()

    def onAstrubMapProcessed(self, event=None):
        self.finish(0, None)

    def onAstrubMapLoadTimeout(self, listener: Listener):
        return self.finish(self.ASTRUB_MAPLOAD_TIMEOUT, f"Load Astrub map '{self.astrubLandingMapId}' timedout!")

    def onGetOutOfIncarnamNpcEnd(self, code, error):
        if error:
            return self.finish(code, error)
        self.onceMapProcessed(
            callback=self.onAstrubMapProcessed,
            mapId=self.astrubLandingMapId,
            timeout=20,
            ontimeout=self.onAstrubMapLoadTimeout
        )

    def run(self) -> bool:
        sa = SubArea.getSubAreaByMapId(PlayedCharacterManager().currentMap.mapId)
        areaId = sa._area.id
        if areaId != self.ankarnamAreaId:
            return self.finish(True, "Already out of ankarnam area")
        NpcDialog().start(
            self.npcMapId,
            self.npcId,
            self.openGoToAstrubActionId,
            # TODO: fix this, it must become a dict matching questions with answers
            [self.goToAstrubReplyId, self.iAmSureReplyId],
            callback=self.onGetOutOfIncarnamNpcEnd,
            parent=self,
        )
