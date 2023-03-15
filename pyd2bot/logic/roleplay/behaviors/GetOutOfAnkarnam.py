from typing import TYPE_CHECKING
from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.NpcDialog import NpcDialog
from pydofus2.com.ankamagames.dofus.datacenter.world.SubArea import SubArea
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import PlayedCharacterManager
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
if TYPE_CHECKING:
    pass

class GetOutOfAnkarnam(AbstractBehavior):

    def __init__(self) -> None:
        super().__init__()
        self.npcId = -20001
        self.npcMapId = 153880835
        self.openGoToAstrubActionId = 3
        self.iAmSureReplyId = 36979
        self.goToAstrubReplyId = 36977
        self.ankarnamAreaId = 45

    def start(self, callback) -> bool:
        if self.running.is_set():
            return self.finish(False, "[GetOutOfAnkarnam] Already running.")
        self.running.set()
        self.callback = callback
        Logger().info("[GetOutOfAnkarnam] Started.")
        sa = SubArea.getSubAreaByMapId(PlayedCharacterManager().currentMap.mapId)
        areaId = sa._area.id
        if areaId != self.ankarnamAreaId:
            return self.finish(True, "[GetOutOfAnkarnam] Already out of ankarnam area")
        NpcDialog().start(
            self.npcMapId, 
            self.npcId, 
            self.openGoToAstrubActionId, 
            [self.iAmSureReplyId, self.goToAstrubReplyId],
            self.finish
        )
