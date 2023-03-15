from time import perf_counter
from typing import TYPE_CHECKING

from pyd2bot.logic.managers.BotConfig import BotConfig
from pydofus2.com.ankamagames.berilia.managers.EventsHandler import Event, EventsHandler
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent,
    KernelEventsManager,
)
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.metaclasses.Singleton import Singleton
from pydofus2.com.ankamagames.jerakine.types.positions.MovementPath import MovementPath

if TYPE_CHECKING:
    from pydofus2.com.ankamagames.dofus.network.types.game.context.roleplay.GameRolePlayHumanoidInformations import (
        GameRolePlayHumanoidInformations,
    )


class BotEventsManager(EventsHandler, metaclass=Singleton):
    MEMBERS_READY = 0
    ALL_PARTY_MEMBERS_IDLE = 1
    ALL_MEMBERS_JOINED_PARTY = 2
    MULE_FIGHT_CONTEXT = 3
    BOT_CONNECTED = 4
    BOT_DOSCONNECTED = 5

    def __init__(self):
        super().__init__()

    def onceAllPartyMembersIdle(self, callback, args=[], originator=None):
        def onEvt(e):
            callback(e, *args)

        return self.once(BotEventsManager.ALL_PARTY_MEMBERS_IDLE, onEvt, originator=originator)

    def oncePartyMemberShowed(self, callback, args=[], originator=None):
        def onActorShowed(e, infos: "GameRolePlayHumanoidInformations"):
            for follower in BotConfig().followers:
                if int(follower.id) == int(infos.contextualId):
                    Logger().info("[BotEventsManager] Party member %s showed" % follower.name)
                    callback(e, *args)

        return KernelEventsManager().on(KernelEvent.ACTORSHOWED, onActorShowed, originator=originator)

    def onceAllMembersJoinedParty(self, callback, args=[], originator=None):
        def onEvt(e):
            callback(e, *args)

        return self.once(BotEventsManager.ALL_MEMBERS_JOINED_PARTY, onEvt, originator=originator)

    def onceFighterMoved(self, fighterId, callback, args=[], originator=None):
        def onEvt(event: Event, movedFighterId, movePath: MovementPath):
            if movedFighterId == fighterId:
                event.listener.delete()
                callback(movePath, *args)

        return KernelEventsManager().on(KernelEvent.FIGHTER_MOVEMENT_APPLIED, onEvt, originator=originator)

    def onceFighterCastedSpell(self, fighterId, cellId, callback, args=[], originator=None):
        def onEvt(event: Event, sourceId, destinationCellId, sourceCellId, spellId):
            if sourceId == fighterId and cellId == destinationCellId:
                event.listener.delete()
                callback(*args)

        return KernelEventsManager().on(KernelEvent.FIGHTER_CASTED_SPELL, onEvt, originator=originator)

    def onceMuleJoinedFightContext(self, tgt_muleId, callback, originator=None):
        def onMuleJoinedFightContext(event: Event, muleId):
            if muleId == tgt_muleId:
                event.listener.delete()
                callback()

        return self.on(BotEventsManager.MULE_FIGHT_CONTEXT, onMuleJoinedFightContext, originator=originator)

    def onceBotConnected(self, instanceId, callback, timeout=None, ontimeout=None, originator=None):
        started = perf_counter()

        def onBotConnected(event: Event, conenctedBotInstanceId):
            if conenctedBotInstanceId == instanceId:
                event.listener.delete()
                callback()
            remaining = perf_counter() - started
            if timeout:
                if remaining > 0:
                    event.listener.armTimer()
                else:
                    ontimeout()

        return self.on(
            BotEventsManager.BOT_CONNECTED,
            onBotConnected,
            timeout=timeout,
            ontimeout=ontimeout,
            originator=originator,
        )

    def onceBotDisconnected(self, instanceId, callback, timeout=None, ontimeout=None, originator=None):
        started = perf_counter()

        def onBotDisconnected(event: Event, disconnectedInstance, connectionType):
            if disconnectedInstance == instanceId:
                event.listener.delete()
                callback()
            if timeout:
                remaining = perf_counter() - started
                if remaining > 0:
                    event.listener.armTimer()
                else:
                    ontimeout()

        return self.on(
            BotEventsManager.BOT_DOSCONNECTED,
            onBotDisconnected,
            timeout=timeout,
            ontimeout=ontimeout,
            originator=originator,
        )
