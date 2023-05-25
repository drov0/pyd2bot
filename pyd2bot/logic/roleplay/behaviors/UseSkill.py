from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.MapMove import MapMove
from pydofus2.com.ankamagames.berilia.managers.EventsHandler import Listener
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayInteractivesFrame import (
    InteractiveElementData, RoleplayInteractivesFrame)    
from pydofus2.com.ankamagames.dofus.network.messages.game.interactive.InteractiveElementUpdatedMessage import \
    InteractiveElementUpdatedMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.interactive.InteractiveUseRequestMessage import \
    InteractiveUseRequestMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.interactive.skill.InteractiveUseWithParamRequestMessage import \
    InteractiveUseWithParamRequestMessage
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


class UseSkill(AbstractBehavior):
    ELEM_TAKEN = 9801
    ELEM_BEING_USED = 9802
    ELEM_UPDATE_TIMEOUT = 66987
    TIMEOUT = 9803
    CANT_USE = 9804
    USE_ERROR = 9805
    MAX_TIMEOUTS = 20
    REQ_TIMEOUT = 7

    def __init__(self) -> None:
        super().__init__()
        self.timeoutsCount = 0
        self.ie = None
        self.useErrorListener = None

    def run(self,
        ie: InteractiveElementData,
        cell=None,
        exactDistination=False,
        waitForSkillUsed=True,
        elementId=None,
        skilluid=None,
    ):
        if ie is None:
            if elementId:
                def onIeFound(ie: InteractiveElementData):
                    self.targetIe = ie
                    self.skillUID = ie.skillUID
                    self.elementId = ie.element.elementId
                    self.elementPosition = ie.position
                    self.element = ie.element
                    self.cell = cell
                    self.exactDistination = exactDistination
                    self.waitForSkillUsed = waitForSkillUsed
                    self.useSkill()
                return self.getInteractiveElement(elementId, skilluid, onIeFound)
            else:
                return self.finish(False, "No interactive element provided")
        self.targetIe = ie
        self.skillUID = ie.skillUID
        self.elementId = ie.element.elementId
        self.elementPosition = ie.position
        self.element = ie.element
        self.cell = cell
        self.exactDistination = exactDistination
        self.waitForSkillUsed = waitForSkillUsed
        self.useSkill()

    def useSkill(self) -> None:
        sendInteractiveUseRequest = True
        cell = self.cell
        if not cell:
            cell, sendInteractiveUseRequest = RoleplayInteractivesFrame.getNearestCellToIe(self.element, self.elementPosition)
            
        if not sendInteractiveUseRequest:
            return self.finish(self.CANT_USE, "Can't use this interactive element")

        def onmoved(errType, error):
            if error:
                return self.finish(errType, error)
            self.requestActivateSkill()

        if self.waitForSkillUsed:
            KernelEventsManager().on(
                KernelEvent.INTERACTIVE_ELEMENT_BEING_USED, 
                self.onUsingInteractive, 
                originator=self
            )
            KernelEventsManager().on(KernelEvent.INTERACTIVE_ELEMENT_USED, self.onUsedInteractive, originator=self)
        MapMove().start(cell, self.exactDistination, callback=onmoved, parent=self)

    def ontimeout(self, listener: Listener):
        self.timeoutsCount += 1
        if self.timeoutsCount > self.MAX_TIMEOUTS:
            return self.finish(self.TIMEOUT, "Request timed out")
        listener.armTimer()
        self.sendRequestSkill()

    def onUsingInteractive(self, event, entityId, usingElementId):
        if self.elementId == usingElementId:
            if MapMove().isRunning():
                MapMove().stop()
            if entityId != PlayedCharacterManager().id:
                self.finish(self.ELEM_BEING_USED, "Someone else is using this element")

    def onUsedInteractive(self, event, entityId, usedElementId):
        if self.elementId == usedElementId:
            self.useErrorListener.delete()
            if MapMove().isRunning():
                MapMove().stop()
            if entityId != PlayedCharacterManager().id:
                self.finish(self.ELEM_TAKEN, "Someone else used this element")
            else:
                KernelEventsManager().once(
                    KernelEvent.INTERACTIVE_ELEM_UPDATE,
                    self.onInteractiveUpdated,
                    timeout=7,
                    ontimeout=self.onElemUpdateWaitTimeout,
                    originator=self,
                )
        
    def onInteractiveUpdated(self, event, ieumsg: InteractiveElementUpdatedMessage):
        Logger().info(f"Elem {ieumsg.interactiveElement.elementId} updated")
        if ieumsg.interactiveElement.elementId == self.elementId:
            for skill in ieumsg.interactiveElement.disabledSkills:
                if skill.skillInstanceUid == self.skillUID:
                    Logger().info("Element farmed successfully")
            self.finish(True, None)

    def onElemUpdateWaitTimeout(self, listener: Listener):
        self.finish(self.ELEM_UPDATE_TIMEOUT, "Elem update wait timedout")

    def onUseError(self, event, elementId):
        if MapMove().isRunning():
            MapMove().stop()
        self.finish(self.USE_ERROR, "Can't use this element, probably not in range")

    def requestActivateSkill(self) -> None:
        if self.waitForSkillUsed:
            self.timeoutsCount = 0
            self.useErrorListener = KernelEventsManager().once(
                KernelEvent.INTERACTIVE_USE_ERROR,
                self.onUseError,
                timeout=self.REQ_TIMEOUT,
                ontimeout=self.ontimeout,
                originator=self,
            )
            self.currentRequestedElementId = self.elementId
        self.sendRequestSkill()
        if not self.waitForSkillUsed:
            super().finish(True, None)

    def sendRequestSkill(self, additionalParam=0):
        if additionalParam == 0:
            iurmsg = InteractiveUseRequestMessage()
            iurmsg.init(int(self.elementId), int(self.skillUID))
            ConnectionsHandler().send(iurmsg)
        else:
            iuwprmsg = InteractiveUseWithParamRequestMessage()
            iuwprmsg.init(int(self.elementId), int(self.skillUID), int(additionalParam))
            ConnectionsHandler().send(iuwprmsg)

    def getInteractiveElement(self, elementId, skilluid, callback) -> InteractiveElementData:
        rpif: "RoleplayInteractivesFrame" = Kernel().worker.getFrameByName("RoleplayInteractivesFrame")
        if rpif is None:
            Logger().warning("No roleplay interactive frame found")
            return KernelEventsManager().onceFramePushed(
                "RoleplayInteractivesFrame",
                self.getInteractiveElement,
                [elementId, skilluid, callback],
                originator=self,
            )
        callback(rpif.getInteractiveElement(elementId, skilluid))
