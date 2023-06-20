from pyd2bot.logic.roleplay.behaviors.skill.UseSkill import UseSkill
from pydofus2.com.ankamagames.atouin.managers.MapDisplayManager import \
    MapDisplayManager
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayInteractivesFrame import \
    CollectableElement
from pydofus2.com.ankamagames.jerakine.pathfinding.Pathfinding import \
    Pathfinding


class CollectableResource:
    def __init__(self, it: CollectableElement):
        self.resource = it
        self._nearestCell = None

    @property
    def reachable(self):
        return self.nearestCell is not None and self.nearestCell.distanceTo(self.position) <= self.resource.skill.range

    @property
    def nearestCell(self):
        if not self._nearestCell:
            movePath = Pathfinding().findPath(PlayedCharacterManager().entity.position, self.position)
            if movePath is None:
                self._nearestCell = None
            self._nearestCell = movePath.end
        return self._nearestCell

    @property
    def position(self):
        return MapDisplayManager().getIdentifiedElementPosition(self.resource.id)

    @property
    def hasRequiredLevel(self):
        PlayedCharacterManager().joblevel(self.resource.skill.parentJobId) >= self.resource.skill.levelMin

    def isFiltered(self, jobFilter):
        jobId = self.resource.skill.parentJobId
        return jobId not in jobFilter or self.resource.id not in jobFilter[jobId]

    @property
    def canCollecte(self):
        return self.resource.enabled and self.hasRequiredLevel and self.reachable

    @property
    def canFarm(self, jobFilter=None):
        if jobFilter:
            return self.canCollecte and not self.isFiltered(jobFilter)
        return self.canCollecte

    def farm(self, callback, caller=None):
        UseSkill().start(
            elementId=self.resource.id,
            skilluid=self.resource.interactiveSkill.skillInstanceUid,
            cell=self.nearestCell.cellId,
            callback=callback,
            parent=caller
        )

    def __hash__(self) -> int:
        return self.resource.id
