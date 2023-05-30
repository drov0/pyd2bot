from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.skill.UseSkill import UseSkill
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.internalDatacenter.taxi.TeleportDestinationWrapper import \
    TeleportDestinationWrapper
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.network.messages.game.dialog.LeaveDialogRequestMessage import \
    LeaveDialogRequestMessage
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


class SaveZaap(AbstractBehavior):
    ZAAP_IE_NOTFOUND = 255555
    
    def __init__(self) -> None:
        super().__init__()

    def run(self) -> bool:
        if Kernel().interactivesFrame:
            self.openCurrMapZaapDialog()
        else:
            KernelEventsManager().onceFramePushed("RoleplayInteractivesFrame", self.openCurrMapZaapDialog, originator=self)

    def openCurrMapZaapDialog(self):
        self.zaapIe = Kernel().interactivesFrame.getZaapIe()
        if not self.zaapIe:
            return self.finish(self.ZAAP_IE_NOTFOUND, "Zaap ie not found in current Map")
        KernelEventsManager().once(
            event_id=KernelEvent.TeleportDestinationList,
            callback=self.onTeleportDestinationList,
            originator=self
        )
        UseSkill().start(ie=self.zaapIe, waitForSkillUsed=False, callback=self.onZaapSkillUsed, parent=self)
        
    def onZaapSkillUsed(self, code, err):
        if err:
            return self.finish(code, err)

    def onZaapSaveResp(self, event_id, destinations: list[TeleportDestinationWrapper], ttype):
        ConnectionsHandler().send(LeaveDialogRequestMessage())
        return KernelEventsManager().on(
            KernelEvent.DIALOG_LEFT,
            lambda _: self.finish(True, None),
            originator=self
        )
        
    def onTeleportDestinationList(self, event_id, destinations: list[TeleportDestinationWrapper], ttype):
        Logger().debug(f"Zaap teleport destinations received.")
        Kernel().zaapFrame.zaapRespawnSaveRequest()
        return KernelEventsManager().once(
            event_id=KernelEvent.TeleportDestinationList,
            callback=self.onZaapSaveResp,
            originator=self
        )
