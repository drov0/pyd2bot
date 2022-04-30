from com.ankamagames.dofus.logic.game.fight.fightEvents.FightEventsHelper import (
    FightEventsHelper,
)
from com.ankamagames.dofus.logic.game.fight.steps.IFightStep import IFightStep
from com.ankamagames.dofus.logic.game.fight.steps.abstract.AbstractDodgePointLossStep import (
    AbstractDodgePointLossStep,
)
from com.ankamagames.dofus.logic.game.fight.types.FightEventEnum import FightEventEnum


class FightActionPointsLossDodgeStep(AbstractDodgePointLossStep, IFightStep):
    def __init__(self, fighterId: float, amount: int):
        super().__init__(fighterId, amount)

    @property
    def stepType(self) -> str:
        return "actionPointsLossDodge"

    def start(self) -> None:
        FightEventsHelper.sendFightEvent(
            FightEventEnum.FIGHTER_AP_LOSS_DODGED,
            [self._fighterId, self._amount],
            self._fighterId,
            self.castingSpellId,
        )
        self.executeCallbacks()
