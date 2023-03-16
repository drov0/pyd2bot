
from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.thriftServer.pyd2botService.ttypes import Character
from pydofus2.com.ankamagames.berilia.managers.EventsHandler import (Event,
                                                                     Listener)
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.network.messages.game.context.fight.GameFightJoinRequestMessage import \
    GameFightJoinRequestMessage
from pydofus2.com.ankamagames.dofus.network.types.game.context.fight.FightCommonInformations import \
    FightCommonInformations
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


class MuleFighter(AbstractBehavior):
    FIGHT_JOIN_TIMEOUT = 3

    def __init__(self):
        super().__init__()
    
    def start(self, leader: Character, callback=None):
        if self.running.is_set():
            return Logger().error("Already running")
        Logger().info("Mule fighter started")
        self.callback = callback
        self.leader = leader
        self.running.set()
        self.checkIfLeaderInFight()
        KernelEventsManager().on(KernelEvent.FIGHT_SWORD_SHOWED, self.onFightSword, originator=self)

    def onFightSword(self, event: Event, infos: FightCommonInformations):
        for team in infos.fightTeams:
            if team.leaderId == self.leader.id:
                self.fightId = infos.fightId
                return self.joinFight()
    
    def onfight(event_id) -> None:
        Logger().info("Leader fight joigned successfully")

    def onJoinFightTimeout(self, listener: Listener) -> None:
        Logger().warning("Join fight request timeout")
        listener.armTimer()
        self.sendJoinFightRequest()
    
    def joinFight(self):
        KernelEventsManager().once(
            KernelEvent.FIGHT_STARTED, 
            self.onfight, 
            timeout=self.FIGHT_JOIN_TIMEOUT, 
            ontimeout=self.onJoinFightTimeout, 
            originator=self
        )
        self.sendJoinFightRequest()

    def sendJoinFightRequest(self):
        gfjrmsg = GameFightJoinRequestMessage()
        gfjrmsg.init(self.leader.id, self.fightId)
        ConnectionsHandler().send(gfjrmsg)

    def checkIfLeaderInFight(self):
        if not PlayedCharacterManager().isFighting and Kernel().entitiesFrame:
            for fightId, fight in Kernel().entitiesFrame._fights.items():
                for team in fight.teams:
                    if team.teamInfos.leaderId == self.leader.id:
                        self.fightId = fightId
                        return self.joinFight()
    
    def stop(self):
        self.finish(True, None)