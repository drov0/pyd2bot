from com.ankamagames.dofus.logic.game.common.misc.DofusEntities import DofusEntities
from com.ankamagames.dofus.logic.game.fight.steps.IFightStep import IFightStep
from com.ankamagames.jerakine.entities.interfaces.IEntity import IEntity
from com.ankamagames.jerakine.logger.Logger import Logger
from com.ankamagames.jerakine.sequencer.AbstractSequencable import AbstractSequencable

logger = Logger(__name__)


class FightRemoveSubEntityStep(AbstractSequencable, IFightStep):

    _fighterId: float

    _category: int

    _slot: int

    def __init__(self, fighterId: float, category: int, slot: int):
        super().__init__()
        self._fighterId = fighterId
        self._category = category
        self._slot = slot

    @property
    def stepType(self) -> str:
        return "removeSubEntity"

    def start(self) -> None:
        self.executeCallbacks()

    @property
    def targets(self) -> list[float]:
        return [self._fighterId]
