from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.UseSkill import UseSkill
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.internalDatacenter.taxi.TeleportDestinationWrapper import \
    TeleportDestinationWrapper
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager


class UseZaap(AbstractBehavior):
    ZAAP_IE_NOTFOUND = 255555
    NOT_RICH_ENOUGH = 788888
    def __init__(self) -> None:
        super().__init__()

    def run(self, dstMapId) -> bool:
        self.dstMapId = dstMapId
        if Kernel().interactivesFrame:
            self.zaapIe = Kernel().interactivesFrame.getZaapIe()
            if not self.zaapIe:
                return self.finish(self.ZAAP_IE_NOTFOUND, "Zaap ie not found in current Map")

            UseSkill().start(self.zaapIe, callback=self.onZaapSkillUsed, parent=self)
        else:
            KernelEventsManager().onceFramePushed("RoleplayInteractivesFrame", self.onPhenixMapReached, originator=self)

    def onZaapSkillUsed(self, code, err):
        if err:
            return self.finish(code, err)
        KernelEventsManager().once(
            event_id=KernelEvent.TeleportDestinationList,
            callback=self.onTeleportDestinationList,
            originator=self
        )
    
    def onTeleportDestinationList(self, destinations: list[TeleportDestinationWrapper], ttype):
        for dst in destinations:
            if dst.mapId == self.dstMapId:
                if dst.cost <= PlayedCharacterManager().characteristics.kamas:
                    return self.finish(self.NOT_RICH_ENOUGH, "Don't have enough kamas to take zaap")
                KernelEventsManager().onceMapProcessed(
                    callback=self.onDestMapProcessed,
                    originator=self,
                )
                Kernel().zaapFrame.teleportRequest(dst.cost, ttype, dst.destinationType, dst.mapId)
    
    def onDestMapProcessed(self, event_id=None):
        return self.finish(True, None)
