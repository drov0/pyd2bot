from typing import TYPE_CHECKING

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.NpcDialog import NpcDialog
from pydofus2.com.ankamagames.dofus.datacenter.world.SubArea import SubArea
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

if TYPE_CHECKING:
    pass

class GetOutOfAnkarnam(AbstractBehavior):
    npcId = -20001
    npcMapId = 153880835
    openGoToAstrubActionId = 3
    iAmSureReplyId = 36979
    goToAstrubReplyId = 36977
    ankarnamAreaId = 45
    
    def __init__(self) -> None:
        super().__init__()

    def run(self) -> bool:
        sa = SubArea.getSubAreaByMapId(PlayedCharacterManager().currentMap.mapId)
        areaId = sa._area.id
        if areaId != self.ankarnamAreaId:
            return self.finish(True, "Already out of ankarnam area")
        NpcDialog().start(
            self.npcMapId, 
            self.npcId, 
            self.openGoToAstrubActionId, 
            [self.iAmSureReplyId, self.goToAstrubReplyId],
            callback=self.finish,
            parent=self
        )
