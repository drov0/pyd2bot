from com.ankamagames.dofus.logic.game.fight.steps.IFightStep import IFightStep
from com.ankamagames.dofus.enums.ActionIds import ActionIds
from com.ankamagames.dofus.kernel.Kernel import Kernel
from com.ankamagames.dofus.logic.game.fight.fightEvents.FightEventsHelper import (
    FightEventsHelper,
)
from com.ankamagames.dofus.logic.game.fight.frames.FightEntitiesFrame import (
    FightEntitiesFrame,
)
from com.ankamagames.dofus.logic.game.fight.managers.BuffManager import BuffManager
from com.ankamagames.dofus.logic.game.fight.types.BasicBuff import BasicBuff
from com.ankamagames.dofus.logic.game.fight.types.FightEventEnum import FightEventEnum
from com.ankamagames.dofus.network.messages.game.context.GameContextRefreshEntityLookMessage import (
    GameContextRefreshEntityLookMessage,
)
from com.ankamagames.dofus.network.types.game.context.fight.GameFightFighterInformations import (
    GameFightFighterInformations,
)
from com.ankamagames.jerakine.sequencer.AbstractSequencable import AbstractSequencable


class FightDispellSpellStep(AbstractSequencable, IFightStep):

    _fighterId: float

    _spellId: int

    _verboseCast: bool

    def __init__(self, fighterId: float, spellId: int, verboseCast: bool):
        super().__init__()
        self._fighterId = fighterId
        self._spellId = spellId
        self._verboseCast = verboseCast

    @property
    def stepType(self) -> str:
        return "dispellSpell"

    def start(self) -> None:
        if self._verboseCast:
            FightEventsHelper.sendFightEvent(
                FightEventEnum.FIGHTER_SPELL_DISPELLED,
                [self._fighterId, self._spellId],
                self._fighterId,
                self.castingSpellId,
            )
        buffs: list = BuffManager().getAllBuff(self._fighterId)
        refreshEntityLook: bool = False
        for buff in buffs:
            if (
                buff.castingSpell.spell.id == self._spellId
                and buff.actionId == ActionIds.ACTION_CHARACTER_ADD_APPEARANCE
            ):
                refreshEntityLook = True
        BuffManager().dispellSpell(self._fighterId, self._spellId, True)
        if refreshEntityLook:
            entitiesFrame: "FightEntitiesFrame"  = (
                Kernel().getWorker().getFrame("FightEntitiesFrame")
            )
            fighterInfos = entitiesFrame.getEntityInfos(self._fighterId)
            gcrelmsg = GameContextRefreshEntityLookMessage()
            gcrelmsg.init(
                self._fighterId, fighterInfos.look
            )
            Kernel().getWorker().getFrame("FightEntitiesFrame").process(gcrelmsg)
        self.executeCallbacks()

    @property
    def targets(self) -> list[float]:
        return [self._fighterId]
