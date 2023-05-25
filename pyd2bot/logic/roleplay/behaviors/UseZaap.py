from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.UseSkill import UseSkill
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.internalDatacenter.taxi.TeleportDestinationWrapper import \
    TeleportDestinationWrapper
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.network.messages.game.dialog.LeaveDialogRequestMessage import \
    LeaveDialogRequestMessage
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


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
            KernelEventsManager().once(
                event_id=KernelEvent.TeleportDestinationList,
                callback=self.onTeleportDestinationList,
                originator=self
            )
            UseSkill().start(self.zaapIe, waitForSkillUsed=False, callback=self.onZaapSkillUsed, parent=self)
        else:
            KernelEventsManager().onceFramePushed("RoleplayInteractivesFrame", self.onPhenixMapReached, originator=self)

    def onZaapSkillUsed(self, code, err):
        if err:
            return self.finish(code, err)

    def onTeleportDestinationList(self, event_id, destinations: list[TeleportDestinationWrapper], ttype):
        Logger().debug(f"Zaap teleport destinations received.")
        for dst in destinations:
            if dst.mapId == self.dstMapId:
                if dst.cost > PlayedCharacterManager().characteristics.kamas:
                    ConnectionsHandler().send(LeaveDialogRequestMessage())
                    err = f"Don't have enough kamas to take zaap, player kamas {PlayedCharacterManager().characteristics.kamas}, teleport cost {dst.cost}!"
                    return KernelEventsManager().on(
                        KernelEvent.DIALOG_LEFT,
                        lambda e: self.finish(self.NOT_RICH_ENOUGH, err),
                        originator=self
                    )
                KernelEventsManager().onceMapProcessed(
                    callback=self.onDestMapProcessed,
                    originator=self,
                )
                return Kernel().zaapFrame.teleportRequest(dst.cost, ttype, dst.destinationType, dst.mapId)
        Logger().error(f"Didnt find dest zaap {dst.mapId} in teleport destinations : {[d.mapId for d in destinations]}")
            
    
    def onDestMapProcessed(self, event_id=None):
        return self.finish(True, None)
