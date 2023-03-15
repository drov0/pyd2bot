from typing import TYPE_CHECKING
from pydofus2.com.ankamagames.atouin.managers.MapDisplayManager import MapDisplayManager
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import (
    PlayedCharacterManager,
)
from pydofus2.com.ankamagames.jerakine.metaclasses.Singleton import Singleton

if TYPE_CHECKING:
    from pyd2bot.logic.roleplay.frames.BotPartyFrame import BotPartyFrame
    from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayEntitiesFrame import (
        RoleplayEntitiesFrame,
    )
    from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayInteractivesFrame import (
        RoleplayInteractivesFrame,
    )
    from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayMovementFrame import (
        RoleplayMovementFrame,
    )


class PlayerAPI(metaclass=Singleton):
    def __init__(self):
        pass

    def isIdle(self) -> bool:
        return self.status == "idle"

    @property
    def rpeframe(self) -> "RoleplayEntitiesFrame":
        return Kernel().worker.getFrameByName("RoleplayEntitiesFrame")

    def isProcessingMapData(self) -> bool:
        return not self.rpeframe.mcidm_processed

    @property
    def status(self) -> str:
        from pyd2bot.logic.roleplay.behaviors.CollectItems import CollectItems
        from pyd2bot.logic.roleplay.behaviors.FarmPath import FarmPath
        from pyd2bot.logic.roleplay.behaviors.GiveItems import GiveItems
        from pyd2bot.logic.roleplay.behaviors.UnloadInBank import UnloadInBank
        from pyd2bot.logic.roleplay.behaviors.AutoRevive import AutoRevive
        from pyd2bot.logic.roleplay.behaviors.AutoTrip import AutoTrip
        from pyd2bot.logic.roleplay.behaviors.ChangeMap import ChangeMap
        from pyd2bot.logic.roleplay.behaviors.MapMove import MapMove
        from pyd2bot.logic.roleplay.behaviors.UseSkill import UseSkill
        from pyd2bot.logic.roleplay.behaviors.CreateNewCharacter import CreateNewCharacter
        from pyd2bot.logic.roleplay.behaviors.NpcDialog import NpcDialog

        bpframe: "BotPartyFrame" = Kernel().worker.getFrameByName("BotPartyFrame")
        mvframe: "RoleplayMovementFrame" = Kernel().worker.getFrameByName("RoleplayMovementFrame")
        iframe: "RoleplayInteractivesFrame" = Kernel().worker.getFrameByName("RoleplayInteractivesFrame")
        if PlayedCharacterManager().isInFight:
            status = "fighting"
        if CreateNewCharacter().isRunning():
            status = f"isCreatingCharacter:{CreateNewCharacter().state.name}"
        elif NpcDialog.getInstance(PlayedCharacterManager().instanceId) and NpcDialog().isRunning():
            status = f"inNpcDialog"
        elif MapDisplayManager().currentDataMap is None:
            status = "loadingMap"
        elif not self.rpeframe:
            status = "outOfRolePlay"
        elif self.isProcessingMapData():
            status = "processingMapData"
        elif bpframe and bpframe.followingLeaderTransition:
            status = f"followingLeaderTransition"
        elif bpframe and bpframe.joiningLeaderVertex is not None:
            status = f"joiningLeaderVertex"
        elif CollectItems.getInstance(PlayedCharacterManager().instanceId) and CollectItems().isRunning():
            status = f"collectingItems from:{CollectItems().guest.name}:{CollectItems().state.name}"
        elif UnloadInBank.getInstance(PlayedCharacterManager().instanceId) and UnloadInBank().isRunning():
            status = f"inBankAutoUnload:{UnloadInBank().state.name}"
        elif GiveItems.getInstance(PlayedCharacterManager().instanceId) and GiveItems().isRunning():
            status = f"inSellerAutoUnload:{GiveItems().state.name}"
        elif AutoRevive.getInstance(PlayedCharacterManager().instanceId) and AutoRevive().isRunning():
            status = "inPhenixAutoRevive"
        elif AutoTrip.getInstance(PlayedCharacterManager().instanceId) and AutoTrip().isRunning():
            status = f"inAutoTripTo:{AutoTrip().dstMapId}"
        elif FarmPath().isRunning():
            status = f"Farm:{FarmPath().state.name}"
        elif ChangeMap.getInstance(PlayedCharacterManager().instanceId) and ChangeMap().isRunning():
            status = f"changingMap to {ChangeMap().dstMapId}"
        elif UseSkill.getInstance(PlayedCharacterManager().instanceId) and UseSkill().isRunning():
            status = f"usingSkill:{UseSkill().skillUID} at {UseSkill().cell}"
        elif MapMove.getInstance(PlayedCharacterManager().instanceId) and MapMove().isRunning():
            status = f"movingToCell:{MapMove().dstCell}"
        elif iframe and iframe._usingInteractive:
            status = "interacting"
        elif mvframe and mvframe.isMoving:
            status = "moving"
        elif mvframe and mvframe.requestType:
            status = mvframe.requestType.name
        else:
            status = "idle"
        return status
