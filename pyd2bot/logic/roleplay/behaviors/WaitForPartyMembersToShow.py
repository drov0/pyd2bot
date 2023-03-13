from typing import TYPE_CHECKING
from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pydofus2.com.ankamagames.berilia.managers.EventsHandler import Listener
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import KernelEvent, KernelEventsManager
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayEntitiesFrame import RoleplayEntitiesFrame
from pydofus2.com.ankamagames.dofus.network.types.game.context.roleplay.GameRolePlayHumanoidInformations import GameRolePlayHumanoidInformations
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
if TYPE_CHECKING:
    pass

class WaitForPartyMembersToShow(AbstractBehavior):
    MEMBER_LEFT_PARTY = 0
    
    def __init__(self) -> None:
        super().__init__()
        self.actorShowedListener: 'Listener' = None
        self.partyMemberLeftPartyListener = None

    def start(self, callback) -> bool:
        if self.running.is_set():
            return self.finish(False, "[WaitForPartyMembersToShow] Already running.")
        self.running.set()
        self.callback = callback
        Logger().debug("[WaitForPartyMembersToShow] Waiting for party members to show up.")
        self.partyMemberLeftPartyListener = KernelEventsManager().once(KernelEvent.PARTY_MEMBER_LEFT, self.onPartyMemberLeft)
        self.actorShowedListener = KernelEventsManager().on(KernelEvent.ACTORSHOWED, self.onActorShowed)

    def onTeamMemberShowed(self, event, infos: "GameRolePlayHumanoidInformations"):
        entitiesFrame: "RoleplayEntitiesFrame" = Kernel().worker.getFrameByName("RoleplayEntitiesFrame")
        if entitiesFrame is None:
            KernelEventsManager().onceFramePushed("RoleplayEntitiesFrame", self.onTeamMemberShowed, [event, infos])
        notShowed = []
        for follower in BotConfig().followers:
            if not entitiesFrame.getEntityInfos(follower.id):
                notShowed.append(follower.name)
        if len(notShowed) > 0:
            return Logger().info(f"[WaitForPartyMembersToShow] Waiting for party members {notShowed} to show up.")
        Logger().info("[WaitForPartyMembersToShow] All party members showed.")
        self.actorShowedListener.delete()
        self.partyMemberLeftPartyListener.delete()
        self.finish(True, None)

    def onActorShowed(self, event, infos: "GameRolePlayHumanoidInformations"):
        Logger().info(f"[WaitForPartyMembersToShow] Actor {infos.name} showed.")
        for follower in BotConfig().followers:
            if int(follower.id) == int(infos.contextualId):
                self.onTeamMemberShowed(event, infos)

    def onPartyMemberLeft(self, event, memberId):
        self.actorShowedListener.delete()
        self.finish(memberId, error=self.MEMBER_LEFT_PARTY)