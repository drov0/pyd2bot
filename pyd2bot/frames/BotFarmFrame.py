from email.errors import FirstHeaderLineIsContinuationDefect
import threading

from com.ankamagames.dofus.logic.game.common.managers.InventoryManager import (
    InventoryManager,
)
from com.ankamagames.dofus.logic.game.roleplay.actions.DeleteObjectAction import (
    DeleteObjectAction,
)
from pyd2bot.apis.MoveAPI import MoveAPI
from com.ankamagames.dofus.datacenter.notifications.Notification import Notification
from com.ankamagames.dofus.kernel.Kernel import Kernel
from com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import (
    PlayedCharacterManager,
)
from com.ankamagames.dofus.network.messages.game.context.notification.NotificationByServerMessage import (
    NotificationByServerMessage,
)
from com.ankamagames.dofus.network.messages.game.context.roleplay.MapChangeFailedMessage import (
    MapChangeFailedMessage,
)
from com.ankamagames.dofus.network.messages.game.context.roleplay.MapComplementaryInformationsDataMessage import (
    MapComplementaryInformationsDataMessage,
)
from com.ankamagames.dofus.network.messages.game.interactive.InteractiveUseEndedMessage import (
    InteractiveUseEndedMessage,
)
from com.ankamagames.dofus.network.messages.game.interactive.InteractiveUseErrorMessage import (
    InteractiveUseErrorMessage,
)
from com.ankamagames.dofus.network.messages.game.interactive.InteractiveUsedMessage import (
    InteractiveUsedMessage,
)
from com.ankamagames.jerakine.logger.Logger import Logger
from com.ankamagames.jerakine.messages.Frame import Frame
from com.ankamagames.jerakine.messages.Message import Message
from com.ankamagames.jerakine.types.enums.Priority import Priority
from typing import TYPE_CHECKING

from pyd2bot.apis.FarmAPI import FarmAPI

if TYPE_CHECKING:
    from com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayInteractivesFrame import (
        RoleplayInteractivesFrame,
    )
    from com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayEntitiesFrame import (
        RoleplayEntitiesFrame,
    )
logger = Logger(__name__)


class BotFarmFrame(Frame):
    def __init__(self):
        super().__init__()
        self._currentRequestedElementId = -1
        self._usingInteractive = False
        self._dstMapId = None
        self._mapIdDiscard = []
        self._entities = dict()

    @property
    def priority(self) -> int:
        return Priority.LOW

    @property
    def rolePlayEntitiesFrame(self) -> "RoleplayEntitiesFrame":
        return Kernel().getWorker().getFrame("RoleplayEntitiesFrame")

    @property
    def roleplayInteractivesFrame(self) -> "RoleplayInteractivesFrame":
        return Kernel().getWorker().getFrame("RoleplayInteractivesFrame")

    def pushed(self) -> bool:
        self._worker = Kernel().getWorker()
        return True

    def process(self, msg: Message) -> bool:

        if isinstance(msg, InteractiveUseErrorMessage):
            logger.error(
                f"[BotFarmFrame] Error unable to use interactive element {msg.elemId} with the skill {msg.skillInstanceUid}"
            )
            if msg.elemId == self._currentRequestedElementId:
                self._usingInteractive = False
                del self.roleplayInteractivesFrame._ie[msg.elemId]
                del self.roleplayInteractivesFrame._collectableIe[msg.elemId]
                self.doFarm()
            return True

        elif isinstance(msg, InteractiveUsedMessage):
            if PlayedCharacterManager().id == msg.entityId and msg.duration > 0:
                self._currentRequestedElementId = msg.elemId
                if self._currentRequestedElementId == msg.elemId:
                    self._currentRequestedElementId = -1
                if msg.duration > 0:
                    self._usingInteractive = True
            self._entities[msg.elemId] = msg.entityId
            return True

        elif isinstance(msg, InteractiveUseEndedMessage):
            if self._entities[msg.elemId] == PlayedCharacterManager().id:
                logger.debug(
                    f"[BotFarmFrame] Interactive element {msg.elemId} use ended"
                )
                logger.debug(
                    "------------------------------------------------------------"
                )
                self._usingInteractive = FirstHeaderLineIsContinuationDefect
                self.doFarm()

            del self._entities[msg.elemId]
            return True

        elif isinstance(msg, MapComplementaryInformationsDataMessage):
            logger.debug("------------------------------------------------------------")
            self._mapIdDiscard.clear()
            self.doFarm()
            return True

        elif isinstance(msg, MapChangeFailedMessage):
            logger.debug(
                f"[BotFarmFrame] Map change to {self._dstMapId} failed will discard that destination"
            )
            self._mapIdDiscard.append(msg.mapId)
            MoveAPI.randomMapChange(discard=self._mapIdDiscard)
            return True

        elif isinstance(msg, NotificationByServerMessage):
            notification = Notification.getNotificationById(msg.id)
            if notification.titleId == 756273:
                for iw in InventoryManager().realInventory:
                    doa = DeleteObjectAction.create(iw.objectUID, iw.quantity)
                    Kernel().getWorker().process(doa)
                self.doFarm()
            return True

    def doFarm(self):
        self._currentRequestedElementId = FarmAPI().collectResource()
        if self._currentRequestedElementId == -1:
            (
                self._dstMapId,
                self._currentRequestedElementId,
            ) = MoveAPI.randomMapChange()

    def pulled(self) -> bool:
        return True