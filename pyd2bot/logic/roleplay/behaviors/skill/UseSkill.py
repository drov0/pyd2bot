from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.movement.MapMove import MapMove
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.berilia.managers.Listener import Listener
from pydofus2.com.ankamagames.dofus.datacenter.interactives.Interactive import \
    Interactive
from pydofus2.com.ankamagames.dofus.datacenter.jobs.Skill import Skill
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
from pydofus2.com.ankamagames.jerakine.pathfinding.Pathfinding import \
    Pathfinding
from pydofus2.mapTools import MapTools


class UseSkill(AbstractBehavior):
    ELEM_TAKEN = 9801
    ELEM_BEING_USED = 9802
    ELEM_UPDATE_TIMEOUT = 66987
    NO_ENABLED_SKILLS = 668889
    UNREACHABLE_IE = 669874
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

    def run(
        self,
        ie: InteractiveElementData = None,
        cell=None,
        exactDistination=False,
        waitForSkillUsed=True,
        elementId=None,
        skilluid=None,
    ):
        if ie is None:
            if elementId and skilluid:
                def onIeFound(ie: InteractiveElementData):
                    self.targetIe: InteractiveElementData = ie
                    self.skillUID = ie.skillUID
                    self.elementId = ie.element.elementId
                    self.elementPosition = ie.position
                    self.element = ie.element
                    self.skillId = ie.skillId
                    self.cell = cell
                    self.exactDistination = exactDistination
                    self.waitForSkillUsed = waitForSkillUsed
                    self._useSkill()
                return self.getInteractiveElement(elementId, skilluid, onIeFound)
            else:
                return self.finish(False, "No interactive element provided")
        self.targetIe: InteractiveElementData = ie
        self.skillUID = ie.skillUID
        self.skillId = ie.skillId
        self.elementId = ie.element.elementId
        self.elementPosition = ie.position
        self.element = ie.element
        self.cell = cell
        self.exactDistination = exactDistination
        self.waitForSkillUsed = waitForSkillUsed
        self._useSkill()

    def _useSkill(self) -> None:
        cell = self.cell
        if self.targetIe.element.enabledSkills:
            skillId = self.targetIe.element.enabledSkills[0].skillId
            skill = Skill.getSkillById(skillId)
            playerPos = PlayedCharacterManager().entity.position
            Logger().debug(f"Using {skill.name}, range {skill.range}, id {skill.id}")
            if skill.id in [211, 184] :
                mp, _ = Kernel().interactivesFrame.getNearestCellToIe(self.element, self.elementPosition)
                cell = mp.cellId
            if not cell:
                movePath = Pathfinding().findPath(playerPos, self.elementPosition)
                cell = movePath.end.cellId
                if self.elementPosition.distanceToCell(movePath.end) > skill.range:
                    return self.finish(self.UNREACHABLE_IE, "Unable to find cell close enough to use element", iePosition=self.elementPosition)
            def onmoved(code, error):
                if error:
                    return self.finish(code, error)
                self.requestActivateSkill()
            if self.waitForSkillUsed:
                self.on(KernelEvent.IElemBeingUsed, self.onUsingInteractive,)
                self.on(KernelEvent.InteractiveElementUsed, self.onUsedInteractive)
            self.mapMove(destCell=cell, exactDistination=False, callback=onmoved)
        else:
            self.finish(self.NO_ENABLED_SKILLS, f"Interactive element has no enabled skills!")

    def onUsingInteractive(self, event, entityId, usingElementId):
        if self.elementId == usingElementId:
            if MapMove().isRunning():
                MapMove().stop()
            if entityId != PlayedCharacterManager().id:
                self.finish(self.ELEM_BEING_USED, "Someone else is using this element")

    def onUsedInteractive(self, event, entityId, usedElementId):
        if self.elementId == usedElementId:
            if entityId != PlayedCharacterManager().id:
                if self.elementId in Kernel().interactivesFrame._statedElm:
                    if MapMove().isRunning():
                        MapMove().stop()
                    self.finish(self.ELEM_TAKEN, "Someone else used this element")
            else:            
                if self.useErrorListener:
                    self.useErrorListener.delete()
                if self.elementId in Kernel().interactivesFrame._statedElm:
                    if self.targetIe.element.enabledSkills[0].skillId not in [114]:
                        self.once(
                            KernelEvent.InteractiveElemUpdate,
                            self.onInteractiveUpdated,
                            timeout=7,
                            ontimeout=self.onElemUpdateWaitTimeout,
                        )
                else:
                    self.finish(True, None)

    def onInteractiveUpdated(self, event, ieumsg: InteractiveElementUpdatedMessage):
        if ieumsg.interactiveElement.elementId == self.elementId:
            for skill in ieumsg.interactiveElement.disabledSkills:
                if skill.skillInstanceUid == self.skillUID:
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
            self.useErrorListener = self.once(
                KernelEvent.InteractiveUseError,
                self.onUseError,
                timeout=self.REQ_TIMEOUT,
                ontimeout=lambda _: self.finish(self.TIMEOUT, "Request timed out"),
                retryAction=self.sendRequestSkill,
                retryNbr=self.MAX_TIMEOUTS,
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
