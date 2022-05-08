from time import sleep
from com.ankamagames.dofus.logic.common.frames.LatencyFrame import LatencyFrame
from com.ankamagames.dofus.logic.common.managers.StatsManager import StatsManager
from com.ankamagames.dofus.logic.connection.managers.AuthentificationManager import (
    AuthentificationManager,
)
from com.ankamagames.dofus.logic.game.common.misc.DofusEntities import DofusEntities
from com.ankamagames.dofus.logic.game.fight.managers.FightersStateManager import (
    FightersStateManager,
)
import com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager as pcm
from com.ankamagames.dofus.network.Metadata import Metadata
from com.ankamagames.jerakine.network.messages.Worker import Worker
from com.ankamagames.jerakine.metaclasses.Singleton import Singleton
from com.ankamagames.jerakine.logger.Logger import Logger
from com.ankamagames.jerakine.utils.display.FrameIdManager import FrameIdManager

logger = Logger("Dofus2")


class Kernel(metaclass=Singleton):
    _worker: Worker = Worker()
    beingInReconection: bool = False

    def getWorker(self) -> Worker:
        return self._worker

    def panic(self, errorId: int = 0, panicArgs: list = None) -> None:
        from com.ankamagames.dofus.kernel.net.ConnectionsHandler import (
            ConnectionsHandler,
        )

        self._worker.clear()
        ConnectionsHandler.closeConnection()

    def init(self) -> None:
        FrameIdManager()
        self._worker.clear()
        self.addInitialFrames()
        logger.info(f"Using protocole #{Metadata.PROTOCOL_BUILD}, built on {Metadata.PROTOCOL_DATE}")

    def reset(
        self,
        messagesToDispatchAfter: list = None,
        autoRetry: bool = False,
        reloadData: bool = False,
    ) -> None:
        import com.ankamagames.dofus.logic.game.fight.managers.CurrentPlayedFighterManager as cpfm
        from com.ankamagames.dofus.logic.game.fight.managers.SpellModifiersManager import SpellModifiersManager
        from com.ankamagames.dofus.internalDatacenter.items.ItemWrapper import ItemWrapper

        logger.debug("[KERNEL] Resetting ...")
        # TODO : missing feature manager reset here
        StatsManager.clear()
        SpellModifiersManager.clear()
        if not autoRetry:
            AuthentificationManager.clear()
        FightersStateManager().endFight()
        cpfm.CurrentPlayedFighterManager().endFight()
        pcm.PlayedCharacterManager.clear()
        DofusEntities.reset()
        ItemWrapper.clearCache()
        self._worker.clear()
        self.addInitialFrames()
        self.beingInReconection = False
        if messagesToDispatchAfter is not None and len(messagesToDispatchAfter) > 0:
            for msg in messagesToDispatchAfter:
                self._worker.process(msg)

    def addInitialFrames(self) -> None:
        import com.ankamagames.dofus.logic.connection.frames.DisconnectionHandlerFrame as dhF
        from com.ankamagames.dofus.logic.connection.frames.AuthentificationFrame import (
            AuthentificationFrame,
        )
        from com.ankamagames.dofus.logic.common.frames.CleanupCrewFrame import (
            CleanupCrewFrame,
        )
        from com.ankamagames.dofus.logic.common.frames.QueueFrame import QueueFrame

        logger.debug("[KERNEL] Adding initial frames ...")
        if not self._worker.contains("LatencyFrame"):
            self._worker.addFrame(LatencyFrame())
        self._worker.addFrame(AuthentificationFrame())
        self._worker.addFrame(QueueFrame())
        self._worker.addFrame(dhF.DisconnectionHandlerFrame())
        if not self._worker.contains("CleanupCrewFrame"):
            self._worker.addFrame(CleanupCrewFrame())
