from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.movement.AutoTrip import AutoTrip
from pyd2bot.logic.roleplay.behaviors.skill.UseSkill import UseSkill
from pyd2bot.misc.Localizer import Localizer
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.dofus.datacenter.world.Phoenix import Phoenix
from pydofus2.com.ankamagames.dofus.datacenter.world.SubArea import SubArea
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.network.enums.PlayerLifeStatusEnum import \
    PlayerLifeStatusEnum
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.death.GameRolePlayFreeSoulRequestMessage import \
    GameRolePlayFreeSoulRequestMessage
from pydofus2.com.ankamagames.jerakine.benchmark.BenchmarkTimer import \
    BenchmarkTimer
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


class AutoRevive(AbstractBehavior):

    def __init__(self) -> None:
        super().__init__()
        self.requestTimer = None

    def run(self) -> bool:
        self.phenixMapId = Kernel().playedCharacterUpdatesFrame._phenixMapId
        if not PlayedCharacterManager().currentMap:
            return self.onceMapProcessed(self.start)
        self.on(KernelEvent.PlayerStateChanged, self.onPlayerStateChange)
        if PlayerLifeStatusEnum(PlayedCharacterManager().state) == PlayerLifeStatusEnum.STATUS_PHANTOM:
            Logger().debug(f"Autotravelling to phenix map {self.phenixMapId}")
            self.autoTrip(dstMapId=self.phenixMapId, dstZoneId=1, callback=self.onPhenixMapReached)
        elif PlayerLifeStatusEnum(PlayedCharacterManager().state) == PlayerLifeStatusEnum.STATUS_TOMBSTONE:
            self.onceMapProcessed(self.onCimetaryMapLoaded)
            self.releaseSoulRequest()

    def onPlayerStateChange(self, event, playerState: PlayerLifeStatusEnum, phenixMapId):
        self.phenixMapId = phenixMapId
        Logger().debug(f"Phoenix mapId : {phenixMapId}")
        if playerState == PlayerLifeStatusEnum.STATUS_PHANTOM:
            Logger().info(f"Player saoul released wating for cimetary map to load.")
        elif playerState == PlayerLifeStatusEnum.STATUS_ALIVE_AND_KICKING:
            Logger().info("Player is alive and kicking.")
            self.finish(True, None)

    def onCimetaryMapLoaded(self, event_id=None):
        Logger().debug(f"Cimetary map loaded.")
        if self.requestTimer:
            self.requestTimer.cancel()
        self.autoTrip(dstMapId=self.phenixMapId, dstZoneId=1, callback=self.onPhenixMapReached)

    def onPhenixMapReached(self, code, error):
        if error:
            return self.finish(code, error)
        if Kernel().interactivesFrame:
            reviveIE = Kernel().interactivesFrame.getReviveIe()
            def onPhenixSkillUsed(code, error, iePosition=None):
                if error:
                    return self.finish(code, error)
                Logger().info("Phenix revive skill used")
            self.useSkill(ie=reviveIE, callback=onPhenixSkillUsed)
        else:
            self.onceFramePushed("RoleplayInteractivesFrame", self.onPhenixMapReached)

    def releaseSoulRequest(self):
        def ontimeout():
            self.finish(False, "Player release saoul request timeout!")
        self.requestTimer = BenchmarkTimer(20, ontimeout)
        self.requestTimer.start()
        ConnectionsHandler().send(GameRolePlayFreeSoulRequestMessage())
