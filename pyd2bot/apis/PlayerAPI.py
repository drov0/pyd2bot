
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import PlayedCharacterManager
from pydofus2.com.ankamagames.atouin.managers.MapDisplayManager import MapDisplayManager
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayEntitiesFrame import RoleplayEntitiesFrame
    from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayInteractivesFrame import RoleplayInteractivesFrame
    from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayMovementFrame import RoleplayMovementFrame
    from pyd2bot.logic.roleplay.frames.BotFarmPathFrame import BotFarmPathFrame
    from pyd2bot.logic.roleplay.frames.BotPartyFrame import BotPartyFrame
    from pyd2bot.logic.roleplay.frames.BotUnloadInBankFrame import BotUnloadInBankFrame
    from pyd2bot.logic.roleplay.frames.BotUnloadInSellerFrame import BotUnloadInSellerFrame
    from pyd2bot.logic.roleplay.frames.BotSellerCollectFrame import BotSellerCollectFrame

class PlayerAPI:

    @staticmethod
    def status() -> str:
        bpframe : 'BotPartyFrame' = Kernel().getWorker().getFrame("BotPartyFrame")
        mvframe : 'RoleplayMovementFrame' = Kernel().getWorker().getFrame("RoleplayMovementFrame")
        iframe  : 'RoleplayInteractivesFrame' = Kernel().getWorker().getFrame("RoleplayInteractivesFrame")
        rpeframe : 'RoleplayEntitiesFrame' = Kernel().getWorker().getFrame("RoleplayEntitiesFrame")
        bfpf : 'BotFarmPathFrame' = Kernel().getWorker().getFrame("BotFarmPathFrame")
        if MapDisplayManager().currentDataMap is None:
            status = "loadingMap"
        elif rpeframe and not rpeframe.mcidm_processessed:
            status = "processingMapComplementaryData"
        elif PlayedCharacterManager().isInFight:
            status = "fighting"
        elif bpframe and bpframe.followingLeaderTransition:
            status = f"inTransition:{bpframe.followingLeaderTransition}"
        elif bpframe and bpframe.joiningLeaderVertex is not None:
            status = f"joiningLeaderVertex:{bpframe.joiningLeaderVertex}"
        elif Kernel().getWorker().getFrame("BotSellerCollectFrame"):
            f : "BotSellerCollectFrame" = Kernel().getWorker().getFrame("BotSellerCollectFrame")
            status = "collectingSellerItems:" + f.state.name
        elif Kernel().getWorker().getFrame("BotUnloadInBankFrame"):
            f : "BotUnloadInBankFrame" = Kernel().getWorker().getFrame("BotUnloadInBankFrame")
            status = "inBankAutoUnload:" + f.state.name
        elif Kernel().getWorker().getFrame("BotUnloadInSellerFrame"):
            f : "BotUnloadInSellerFrame" = Kernel().getWorker().getFrame("BotUnloadInSellerFrame")
            status = "inSellerAutoUnload:" + f.state.name
        elif Kernel().getWorker().getFrame("BotPhenixAutoRevive"):
            status = "inPhenixAutoRevive"
        elif Kernel().getWorker().getFrame("BotAutoTripFrame"):
            status = "inAutoTrip"
        elif bfpf and bfpf._followinMonsterGroup:
            status = "followingMonsterGroup"
        elif bfpf and bfpf._followingIe:
            status = "followingIe"
        elif iframe and iframe._usingInteractive:
            status = "interacting"
        elif mvframe and mvframe._isMoving:
            status = "moving"
        elif mvframe and mvframe._wantToChangeMap:
            status = "changingMap"
        else:
            status = "idle"
        return status