from typing import TYPE_CHECKING, Tuple

import com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayInteractivesFrame as riF
from com.ankamagames.atouin.managers.MapDisplayManager import MapDisplayManager
from com.ankamagames.atouin.messages.AdjacentMapClickMessage import AdjacentMapClickMessage
from com.ankamagames.atouin.messages.CellClickMessage import CellClickMessage
from com.ankamagames.atouin.utils.DataMapProvider import DataMapProvider
from com.ankamagames.dofus.datacenter.jobs.Skill import Skill
from com.ankamagames.dofus.internalDatacenter.DataEnum import DataEnum
from com.ankamagames.dofus.kernel.Kernel import Kernel
from com.ankamagames.dofus.kernel.net.ConnectionsHandler import ConnectionsHandler
from com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import PlayedCharacterManager
from com.ankamagames.dofus.logic.game.common.misc.DofusEntities import DofusEntities
from com.ankamagames.dofus.logic.game.roleplay.messages.InteractiveElementActivationMessage import (
    InteractiveElementActivationMessage,
)
from com.ankamagames.dofus.network.types.game.interactive.InteractiveElement import InteractiveElement

if TYPE_CHECKING:
    from com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayContextFrame import (
        RoleplayContextFrame,
    )

from com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayMovementFrame import RoleplayMovementFrame
from com.ankamagames.dofus.network.messages.game.context.fight.GameFightJoinRequestMessage import (
    GameFightJoinRequestMessage,
)
from com.ankamagames.dofus.network.messages.game.context.roleplay.MapComplementaryInformationsDataMessage import (
    MapComplementaryInformationsDataMessage,
)
from com.ankamagames.dofus.network.messages.game.context.roleplay.MapFightStartPositionsUpdateMessage import (
    MapFightStartPositionsUpdateMessage,
)
from com.ankamagames.dofus.network.messages.game.inventory.exchanges.ExchangeOnHumanVendorRequestMessage import (
    ExchangeOnHumanVendorRequestMessage,
)
from com.ankamagames.dofus.network.types.game.context.fight.FightStartingPositions import FightStartingPositions
from com.ankamagames.dofus.network.types.game.context.roleplay.GameRolePlayActorInformations import (
    GameRolePlayActorInformations,
)
from com.ankamagames.dofus.network.types.game.context.roleplay.GameRolePlayGroupMonsterInformations import (
    GameRolePlayGroupMonsterInformations,
)
from com.ankamagames.dofus.types.entities.AnimatedCharacter import AnimatedCharacter
from com.ankamagames.jerakine.entities.messages.EntityClickMessage import EntityClickMessage
from com.ankamagames.jerakine.logger.Logger import Logger
from com.ankamagames.jerakine.messages.events.FramePushedEvent import FramePushedEvent
from com.ankamagames.jerakine.messages.Frame import Frame
from com.ankamagames.jerakine.messages.Message import Message
from com.ankamagames.jerakine.types.enums.Priority import Priority
from com.ankamagames.jerakine.types.positions.MapPoint import MapPoint

logger = Logger("Dofus2")


class RoleplayWorldFrame(Frame):

    NO_CURSOR: int = -1

    FIGHT_CURSOR: int = 3

    NPC_CURSOR: int = 1

    DIRECTIONAL_PANEL_ID: int = 316

    _playerEntity: AnimatedCharacter

    _playerName: str

    _allowOnlyCharacterInteraction: bool

    _fightPositions: FightStartingPositions

    _fightPositionsVisible: bool

    pivotingCharacter: bool

    def __init__(self):
        super().__init__()

    @property
    def mouseOverEntityId(self) -> float:
        return self._mouseOverEntityId

    @property
    def allowOnlyCharacterInteraction(self) -> bool:
        return self._allowOnlyCharacterInteraction

    @allowOnlyCharacterInteraction.setter
    def allowOnlyCharacterInteraction(self, pAllow: bool) -> None:
        self._allowOnlyCharacterInteraction = pAllow

    @property
    def priority(self) -> int:
        return Priority.NORMAL

    @property
    def roleplayContextFrame(self) -> "RoleplayContextFrame":
        from com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayContextFrame import RoleplayContextFrame

        return Kernel().getWorker().getFrame("RoleplayContextFrame")

    @property
    def roleplayMovementFrame(self) -> RoleplayMovementFrame:
        return Kernel().getWorker().getFrame("RoleplayMovementFrame")

    def pushed(self) -> bool:
        self._allowOnlyCharacterInteraction = False
        self.cellClickEnabled = True
        return True

    def process(self, msg: Message) -> bool:

        if isinstance(msg, CellClickMessage):
            if self.allowOnlyCharacterInteraction:
                return False
            if self.cellClickEnabled:
                climsg = msg
                self.roleplayMovementFrame.resetNextMoveMapChange()
                self.roleplayMovementFrame.setFollowingInteraction(None)
                self.roleplayMovementFrame.askMoveTo(MapPoint.fromCellId(climsg.cellId))
            return True

        if isinstance(msg, AdjacentMapClickMessage):
            if self.allowOnlyCharacterInteraction:
                return False
            if self.cellClickEnabled:
                amcmsg = msg
                playedEntity = DofusEntities.getEntity(PlayedCharacterManager().id)
                if not playedEntity:
                    logger.warn("The player tried to move before its character was added to the scene. Aborting.")
                    return False
                self.roleplayMovementFrame.setNextMoveMapChange(amcmsg.adjacentMapId)
                if playedEntity.position != MapPoint.fromCellId(amcmsg.cellId):
                    self.roleplayMovementFrame.setFollowingInteraction(None)
                    self.roleplayMovementFrame.askMoveTo(MapPoint.fromCellId(amcmsg.cellId))
                else:
                    self.roleplayMovementFrame.setFollowingInteraction(None)
                    self.roleplayMovementFrame.askMapChange()
            return True

        if isinstance(msg, MapComplementaryInformationsDataMessage):
            mcidmsg = msg
            self._fightPositions = mcidmsg.fightStartPositions
            return False

        if isinstance(msg, MapFightStartPositionsUpdateMessage):
            mfspmsg = msg
            if PlayedCharacterManager().currentMap and mfspmsg.mapId == PlayedCharacterManager().currentMap.mapId:
                self._fightPositions = mfspmsg.fightStartPositions
            return True

        if isinstance(msg, EntityClickMessage):
            ecmsg = msg
            entityc = ecmsg.entity
            if isinstance(entityc, AnimatedCharacter):
                entityc = entityc
            entityClickInfo = self.roleplayContextFrame.entitiesFrame.getEntityInfos(entityc.id)
            # If entity clicked is a fight not yet started
            if self.roleplayContextFrame.entitiesFrame.isFight(entityc.id):
                fightId = self.roleplayContextFrame.entitiesFrame.getFightId(entityc.id)
                fightTeamLeader = self.roleplayContextFrame.entitiesFrame.getFightLeaderId(entityc.id)
                gfjrmsg = GameFightJoinRequestMessage()
                gfjrmsg.init(fightTeamLeader, fightId)
                playerEntity3 = DofusEntities.getEntity(PlayedCharacterManager().id)
                if playerEntity3:
                    self.roleplayMovementFrame.setFollowingMessage(gfjrmsg)
                    playerEntity3
                else:
                    ConnectionsHandler.getConnection().send(gfjrmsg)
            elif entityc.id != PlayedCharacterManager().id:
                self.roleplayMovementFrame.setFollowingInteraction(None)
                if isinstance(entityClickInfo, GameRolePlayActorInformations) and isinstance(
                    entityClickInfo, GameRolePlayGroupMonsterInformations
                ):
                    self.roleplayMovementFrame.setFollowingMonsterFight(entityc)
                self.roleplayMovementFrame.askMoveTo(entityc.position)
            return True

        if isinstance(msg, InteractiveElementActivationMessage):
            sendInteractiveUseRequest = True
            ieamsg = msg
            interactiveFrame: riF.RoleplayInteractivesFrame = (
                Kernel().getWorker().getFrame("RoleplayInteractivesFrame")
            )
            if interactiveFrame.usingInteractive:
                logger.debug("Interactive element already in use")
            if not (interactiveFrame and interactiveFrame.usingInteractive):
                playerEntity = PlayedCharacterManager().entity
                if not playerEntity:
                    return True
                nearestCell, sendInteractiveUseRequest = self.getNearestCellToIe(msg.interactiveElement, msg.position)
                if sendInteractiveUseRequest:
                    self.roleplayMovementFrame.setFollowingInteraction(
                        {
                            "ie": ieamsg.interactiveElement,
                            "skillInstanceId": ieamsg.skillInstanceId,
                            "additionalParam": ieamsg.additionalParam,
                        }
                    )
                self.roleplayMovementFrame.resetNextMoveMapChange()
                self.roleplayMovementFrame.askMoveTo(nearestCell)
            return True

        return False

    def pulled(self) -> bool:
        return True

    def onFramePushed(self, pEvent: FramePushedEvent) -> None:
        from com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayEntitiesFrame import RoleplayEntitiesFrame

        if isinstance(pEvent.frame, RoleplayEntitiesFrame):
            pEvent.currentTarget.removeEventListener(FramePushedEvent.EVENT_FRAME_PUSHED, self.onFramePushed)

    def onMerchantPlayerBuyClick(self, vendorId: float, vendorCellId: int) -> None:
        eohvrmsg: ExchangeOnHumanVendorRequestMessage = ExchangeOnHumanVendorRequestMessage()
        eohvrmsg.initExchangeOnHumanVendorRequestMessage(vendorId, vendorCellId)
        ConnectionsHandler.getConnection().send(eohvrmsg)

    def getNearestCellToIe(self, ie: InteractiveElement, iePos: MapPoint) -> Tuple[MapPoint, bool]:
        forbiddenCellsIds = list()
        cells = MapDisplayManager().dataMap.cells
        dmp = DataMapProvider()
        sendInteractiveUseRequest = True
        for i in range(8):
            mp = iePos.getNearestCellInDirection(i)
            if mp:
                cellData = cells[mp.cellId]
                forbidden = not cellData.mov or cellData.farmCell
                if not forbidden:
                    numWalkableCells = 8
                    for j in range(8):
                        mp2 = mp.getNearestCellInDirection(j)
                        if mp2 and (
                            not dmp.pointMov(mp2.x, mp2.y, True, mp.cellId)
                            or not dmp.pointMov(mp2.x - 1, mp2.y, True, mp.cellId)
                            and not dmp.pointMov(mp2.x, mp2.y - 1, True, mp.cellId)
                        ):
                            numWalkableCells -= 1
                    if not numWalkableCells:
                        forbidden = True
                if forbidden:
                    if not forbiddenCellsIds:
                        forbiddenCellsIds = []
                    forbiddenCellsIds.append(mp.cellId)
        ieCellData = cells[iePos.cellId]
        skills = ie.enabledSkills
        minimalRange = 63
        for skillForRange in skills:
            skillData = Skill.getSkillById(skillForRange.skillId)
            if skillData:
                if not skillData.useRangeInClient:
                    minimalRange = 1
                elif skillData.range < minimalRange:
                    minimalRange = skillData.range
        distanceElementToPlayer = iePos.distanceToCell(PlayedCharacterManager().entity.position)
        if distanceElementToPlayer <= minimalRange and (not ieCellData.mov or ieCellData.farmCell):
            nearestCell = PlayedCharacterManager().entity.position
        else:
            nearestCell = iePos.getNearestFreeCellInDirection(
                iePos.advancedOrientationTo(PlayedCharacterManager().entity.position),
                DataMapProvider(),
                True,
                True,
                False,
                forbiddenCellsIds,
            )
            if minimalRange > 1:
                for _ in range(minimalRange - 1):
                    forbiddenCellsIds.append(nearestCell.cellId)
                    nearestCell = nearestCell.getNearestFreeCellInDirection(
                        nearestCell.advancedOrientationTo(PlayedCharacterManager().entity.position, False),
                        DataMapProvider(),
                        True,
                        True,
                        False,
                        forbiddenCellsIds,
                    )
                    if not nearestCell or nearestCell.cellId == PlayedCharacterManager().entity.position.cellId:
                        break
        if len(skills) == 1 and skills[0].skillId == DataEnum.SKILL_POINT_OUT_EXIT:
            nearestCell.cellId = PlayedCharacterManager().entity.position.cellId
            sendInteractiveUseRequest = False
        if not nearestCell or nearestCell.cellId in forbiddenCellsIds:
            nearestCell = iePos
        return nearestCell, sendInteractiveUseRequest
