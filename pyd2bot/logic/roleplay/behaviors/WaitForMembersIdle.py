from typing import TYPE_CHECKING

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.thriftServer.pyd2botService.ttypes import Character
from pydofus2.com.ankamagames.atouin.managers.MapDisplayManager import \
    MapDisplayManager
from pydofus2.com.ankamagames.berilia.managers.EventsHandler import Listener
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionType import \
    ConnectionType
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

if TYPE_CHECKING:
    pass

class WaitForMembersIdle(AbstractBehavior):
    GET_STATUS_TIMEOUT = 992
    MEMBER_RECONNECT_WAIT_TIMEOUT = 30
    MEMBER_DISCONNECTED = 997
    
    def __init__(self) -> None:
        super().__init__()
        self.actorShowedListener: 'Listener' = None
        self.partyMemberLeftPartyListener = None
        self.memberStatus = dict[str, str]()
        self.members = list[Character]()

    def start(self, members: list[Character], callback) -> bool:
        if self.running.is_set():
            return self.finish(self.ALREADY_RUNNING, "Already running")
        self.running.set()
        self.callback = callback
        self.members = members
        Logger().debug("Waiting for party members Idle.")
        self.fetchStatuses()
        
    def fetchStatuses(self):
        if not self.isRunning():
            return
        self.memberStatus = {follower.login: None for follower in self.members}
        for member in self.members:
            if not self.isRunning():
                return
            if not Kernel().rpcFrame:
                if Kernel().worker.terminated.is_set():
                    return Logger().warning("Worker terminated while fetching player status")
                return KernelEventsManager().onceFramePushed("BotRPCFrame", self.fetchStatuses, originator=self)
            status = self.getMuleStatus(member.login)
            self.memberStatus[member.login] = status
        self.checkMembersIdle()

    def checkMembersIdle(self):
        if not self.isRunning():
            return
        if all(status is not None for status in self.memberStatus.values()):
            nonIdleMemberNames = [f"- {name} : {status}" for name, status in self.memberStatus.items() if status != "idle"]
            if nonIdleMemberNames:
                strlist = "\n".join(nonIdleMemberNames)
                Logger().info(f"Waiting for members :\n{strlist}.")
                if Kernel().worker.terminated.wait(2):
                    return
                self.fetchStatuses()
            else:
                Logger().debug(f"members status : {self.memberStatus}")
                Logger().info(f"All members are idle.")
                return self.finish(True, None)
    
    def getMuleStatus(self, instanceId):
        if not ConnectionsHandler.getInstance(instanceId) or \
            ConnectionsHandler.getInstance(instanceId).connectionType == ConnectionType.DISCONNECTED:
            return "disconnected"
        elif ConnectionsHandler.getInstance(instanceId).connectionType == ConnectionType.TO_LOGIN_SERVER:
            return "authenticating"
        if PlayedCharacterManager.getInstance(instanceId).isInFight:
            return "fighting"
        elif not Kernel.getInstance(instanceId).entitiesFrame:
            return "outOfRolePlay"
        elif MapDisplayManager.getInstance(instanceId).currentDataMap is None:
            return "loadingMap"
        elif not Kernel.getInstance(instanceId).entitiesFrame.mcidm_processed:
            return "processingMapData"
        for behavior in AbstractBehavior.getAllChilds(instanceId):
            if type(behavior).__name__ != "MuleFighter" and behavior.isRunning():
                return behavior.__str__()
        return "idle"
