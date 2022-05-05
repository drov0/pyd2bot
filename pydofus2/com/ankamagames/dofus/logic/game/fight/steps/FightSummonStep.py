from com.ankamagames.atouin.managers.EntitiesManager import EntitiesManager
from com.ankamagames.dofus.internalDatacenter.spells.SpellWrapper import SpellWrapper
from com.ankamagames.dofus.internalDatacenter.stats.EntityStats import EntityStats
from com.ankamagames.dofus.internalDatacenter.stats.Stat import Stat
from com.ankamagames.dofus.kernel.Kernel import Kernel
from com.ankamagames.dofus.logic.common.managers.StatsManager import StatsManager
from com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import (
    PlayedCharacterManager,
)
from com.ankamagames.dofus.logic.game.common.misc.DofusEntities import DofusEntities
from com.ankamagames.dofus.logic.game.fight.fightEvents.FightEventsHelper import (
    FightEventsHelper,
)
from com.ankamagames.dofus.logic.game.fight.frames.FightEntitiesFrame import (
    FightEntitiesFrame,
)
from com.ankamagames.dofus.logic.game.fight.managers.BuffManager import BuffManager
from com.ankamagames.dofus.logic.game.fight.managers.CurrentPlayedFighterManager import (
    CurrentPlayedFighterManager,
)
from com.ankamagames.dofus.logic.game.fight.steps.IFightStep import IFightStep
from com.ankamagames.dofus.logic.game.fight.types.BasicBuff import BasicBuff
from com.ankamagames.dofus.logic.game.fight.types.FightEventEnum import FightEventEnum
from com.ankamagames.dofus.logic.game.fight.types.StateBuff import StateBuff
from com.ankamagames.dofus.network.messages.game.context.fight.character.GameFightShowFighterMessage import (
    GameFightShowFighterMessage,
)
from com.ankamagames.dofus.network.types.game.context.fight.GameFightFighterInformations import (
    GameFightFighterInformations,
)
from com.ankamagames.jerakine.sequencer.AbstractSequencable import AbstractSequencable
from damageCalculation.tools.StatIds import StatIds
from typing import TYPE_CHECKING

if TYPE_CHECKING:

    from com.ankamagames.dofus.logic.game.fight.frames.FightBattleFrame import (
        FightBattleFrame,
    )


class FightSummonStep(AbstractSequencable, IFightStep):

    _summonerId: float

    _summonInfos: GameFightFighterInformations

    def __init__(self, summonerId: float, summonInfos: GameFightFighterInformations):
        super().__init__()
        self._summonerId = summonerId
        self._summonInfos = summonInfos

    @property
    def stepType(self) -> str:
        return "summon"

    def start(self) -> None:
        summonedCreature = DofusEntities.getEntity(self._summonInfos.contextualId)
        if summonedCreature:
            summonedCreature.visible = True
        else:
            gfsgmsg = GameFightShowFighterMessage()
            gfsgmsg.init(self._summonInfos)
            Kernel().getWorker().getFrame("FightEntitiesFrame").process(gfsgmsg)
        if EntitiesManager().entitiesScheduledForDestruction.get(
            self._summonInfos.contextualId
        ):
            del EntitiesManager().entitiesScheduledForDestruction[
                self._summonInfos.contextualId
            ]
        SpellWrapper.refreshAllPlayerSpellHolder(self._summonerId)
        fightBattleFrame: "FightBattleFrame" = (
            Kernel().getWorker().getFrame("FightBattleFrame")
        )
        if (
            fightBattleFrame
            and self._summonInfos.contextualId not in fightBattleFrame.deadFightersList
        ):
            fightBattleFrame.deadFightersList.remove(self._summonInfos.contextualId)
            buffs = BuffManager().getAllBuff(self._summonInfos.contextualId)
            for buff in buffs:
                if isinstance(buff, StateBuff):
                    BuffManager().updateBuff(buff)
        summonStats: EntityStats = StatsManager().getStats(
            self._summonInfos.contextualId
        )
        summonLifePoints: float = summonStats.getHealthPoints()
        if self._summonInfos.contextualId == PlayedCharacterManager().id:
            fighterInfos: "GameFightFighterInformations" = (
                FightEntitiesFrame.getCurrentInstance().getEntityInfos(
                    self._summonInfos.contextualId
                )
            )
            stats = StatsManager().getStats(fighterInfos.contextualId)
            if not fighterInfos or not stats or not summonStats:
                super().executeCallbacks()
                return
            CurrentPlayedFighterManager().getSpellCastManager().resetInitialCooldown(
                True
            )
            fighterLifePoints = (
                float(summonStats.getMaxHealthPoints() / 2)
                if summonLifePoints == 0
                else float(summonLifePoints)
            )
            stats.setStat(
                Stat(
                    StatIds.CUR_LIFE,
                    fighterLifePoints
                    - summonStats.getMaxHealthPoints()
                    - summonStats.getStatTotalValue(StatIds.CUR_PERMANENT_DAMAGE),
                )
            )
            if PlayedCharacterManager().id == self._summonInfos.contextualId:
                StatsManager().getStats(PlayedCharacterManager().id).setStat(
                    Stat(
                        StatIds.CUR_LIFE,
                        fighterLifePoints
                        - summonStats.getMaxHealthPoints()
                        - summonStats.getStatTotalValue(StatIds.CUR_PERMANENT_DAMAGE),
                    )
                )
        elif summonLifePoints == 0 and summonStats:
            summonStats.setStat(
                Stat(
                    StatIds.CUR_LIFE,
                    -(
                        summonStats.getMaxHealthPoints()
                        + summonStats.getStatTotalValue(StatIds.CUR_PERMANENT_DAMAGE)
                    )
                    / 2,
                )
            )
        FightEventsHelper().sendFightEvent(
            FightEventEnum.FIGHTER_SUMMONED,
            [self._summonerId, self._summonInfos.contextualId],
            self._summonInfos.contextualId,
            self.castingSpellId,
        )
        self.executeCallbacks()

    @property
    def targets(self) -> list[float]:
        return [self._summonInfos.contextualId]