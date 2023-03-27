from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pydofus2.com.ankamagames.dofus.datacenter.world.SubArea import SubArea
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pyd2bot.logic.roleplay.behaviors._AutoTrip import _AutoTrip

class AutoTrip(AbstractBehavior):
    
    def __init__(self):
        super().__init__()
        
    def run(self, dstMapId, dstZoneId):
        srcSubAreaId = SubArea.getSubAreaByMapId(PlayedCharacterManager().currentMap.mapId)
        srcAreaId = srcSubAreaId._area.id
        dstSubAreaId = SubArea.getSubAreaByMapId(dstMapId)
        dstAreaId = dstSubAreaId._area.id
        from pyd2bot.logic.roleplay.behaviors.GetOutOfAnkarnam import \
            GetOutOfAnkarnam
        if dstAreaId != GetOutOfAnkarnam.ankarnamAreaId and srcAreaId == GetOutOfAnkarnam.ankarnamAreaId:
            Logger().info("Auto trip to an Area out of ankarnam while character is in ankarnam. Need to get it out of there first.")
            def onGotOutOfAnkarnam(code, error):
                if error:
                    return self.finish(code, error)
                _AutoTrip().start(dstMapId, dstZoneId, parent=self.parent, callback=self.callback)
            return GetOutOfAnkarnam().start(callback=onGotOutOfAnkarnam, parent=self)
        _AutoTrip().start(dstMapId, dstZoneId, parent=self.parent, callback=self.callback)