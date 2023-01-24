from pyd2bot.logic.roleplay.frames.BotPartyFrame import BotPartyFrame
from pyd2bot.logic.roleplay.frames.BotUnloadInSellerFrame import BotUnloadInSellerFrame
from pyd2bot.logic.roleplay.messages.SellerCollectedGuestItemsMessage import SellerCollectedGuestItemsMessage
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.network.enums.GameContextEnum import GameContextEnum
from pydofus2.com.ankamagames.dofus.network.enums.PlayerLifeStatusEnum import PlayerLifeStatusEnum
from pydofus2.com.ankamagames.dofus.network.messages.game.context.GameContextCreateMessage import GameContextCreateMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.GameContextDestroyMessage import GameContextDestroyMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.death.GameRolePlayGameOverMessage import (
    GameRolePlayGameOverMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.death.GameRolePlayPlayerLifeStatusMessage import (
    GameRolePlayPlayerLifeStatusMessage,
)
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.items.InventoryWeightMessage import InventoryWeightMessage
from pydofus2.com.ankamagames.jerakine.messages.Frame import Frame
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.messages.Message import Message
from pydofus2.com.ankamagames.jerakine.types.enums.Priority import Priority
from pyd2bot.apis.InventoryAPI import InventoryAPI
from pyd2bot.logic.fight.frames.BotFightFrame import BotFightFrame
from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.frames.BotFarmPathFrame import BotFarmPathFrame
from pyd2bot.logic.roleplay.frames.BotPhenixAutoRevive import BotPhenixAutoRevive
from pyd2bot.logic.roleplay.frames.BotUnloadInBankFrame import BotUnloadInBankFrame
from pyd2bot.logic.roleplay.messages.BankUnloadEndedMessage import BankUnloadEndedMessage

logger = Logger()


class BotWorkflowFrame(Frame):
    def __init__(self):
        self.currentContext = None
        super().__init__()

    def pushed(self) -> bool:
        self._inAutoUnload = False
        self._inPhenixAutoRevive = False
        self._delayedAutoUnlaod = False
        Kernel().worker.addFrame(BotPartyFrame())
        return True

    def pulled(self) -> bool:
        Kernel().worker.removeFrameByName("BotCharacterUpdatesFrame")
        return True

    @property
    def priority(self) -> int:
        return Priority.VERY_LOW

    def triggerUnload(self):
        if BotConfig().path and Kernel().worker.getFrame("BotFarmPathFrame"):
            Kernel().worker.removeFrameByName("BotFarmPathFrame")
        if BotConfig().party and Kernel().worker.getFrame("BotPartyFrame"):
            Kernel().worker.removeFrameByName("BotPartyFrame")
        self._inAutoUnload = True
        logger.warn(f"Inventory is almost full {InventoryAPI.getWeightPercent()}, will trigger auto bank unload...")
        if BotConfig().unloadType == "bank":
            Kernel().worker.addFrame(BotUnloadInBankFrame(True))
        elif BotConfig().unloadType == "seller":
            Kernel().worker.addFrame(BotUnloadInSellerFrame(BotConfig().seller, True))

    def process(self, msg: Message) -> bool:

        if isinstance(msg, GameContextCreateMessage):
            logger.debug("*************************************** GameContext Created ************************************************")
            self.currentContext = msg.context
            if self._delayedAutoUnlaod:
                self._delayedAutoUnlaod = False
                self.triggerUnload()
                return True
            if not self._inAutoUnload and not self._inPhenixAutoRevive:
                if self.currentContext == GameContextEnum.ROLE_PLAY:
                    if BotConfig().party and not Kernel().worker.contains("BotPartyFrame"):
                        Kernel().worker.addFrame(BotPartyFrame())
                    if BotConfig().path and not Kernel().worker.contains("BotFarmPathFrame"):
                        Kernel().worker.addFrame(BotFarmPathFrame(True))
                elif self.currentContext == GameContextEnum.FIGHT:
                    if BotConfig().party and not Kernel().worker.contains("BotPartyFrame"):
                        Kernel().worker.addFrame(BotPartyFrame())
                    Kernel().worker.addFrame(BotFightFrame())
            return True

        elif isinstance(msg, GameContextDestroyMessage):
            logger.debug("*************************************** GameContext Destroyed ************************************************")
            if self.currentContext == GameContextEnum.FIGHT:
                if Kernel().worker.contains("BotFightFrame"):
                    Kernel().worker.removeFrameByName("BotFightFrame")
            elif self.currentContext == GameContextEnum.ROLE_PLAY:
                if Kernel().worker.contains("BotFarmPathFrame"):
                    Kernel().worker.removeFrameByName("BotFarmPathFrame")
            return True

        elif isinstance(msg, InventoryWeightMessage):
            if not self._inAutoUnload:
                WeightPercent = round((msg.inventoryWeight / msg.weightMax) * 100, 2)
                if WeightPercent > 95:
                    if self.currentContext is None:
                        self._delayedAutoUnlaod = True
                        logger.debug("Inventory full but the context is not created yet, so we will delay the unload.")
                        return False
                    self.triggerUnload()
                return True
            else:
                return False

        elif isinstance(msg, (BankUnloadEndedMessage, SellerCollectedGuestItemsMessage)):
            self._inAutoUnload = False
            if BotConfig().path and not Kernel().worker.contains("BotFarmPathFrame"):
                Kernel().worker.addFrame(BotFarmPathFrame(True))
            if BotConfig().party and not Kernel().worker.contains("BotPartyFrame"):
                Kernel().worker.addFrame(BotPartyFrame())

        elif (
            isinstance(msg, GameRolePlayPlayerLifeStatusMessage)
            and (
                PlayerLifeStatusEnum(msg.state) == PlayerLifeStatusEnum.STATUS_TOMBSTONE
                or PlayerLifeStatusEnum(msg.state) == PlayerLifeStatusEnum.STATUS_PHANTOM
            )
        ) or isinstance(msg, GameRolePlayGameOverMessage):
            logger.debug(f"Player is dead, auto reviving...")
            self._inPhenixAutoRevive = True
            if Kernel().worker.contains("BotFarmPathFrame"):
                Kernel().worker.removeFrameByName("BotFarmPathFrame")
            PlayedCharacterManager().state = PlayerLifeStatusEnum(msg.state)
            Kernel().worker.addFrame(BotPhenixAutoRevive())
            return False

        elif (
            isinstance(msg, GameRolePlayPlayerLifeStatusMessage)
            and PlayerLifeStatusEnum(msg.state) == PlayerLifeStatusEnum.STATUS_ALIVE_AND_KICKING
        ):
            logger.debug(f"Player is alive and kicking, returning to work...")
            self._inPhenixAutoRevive = False
            if Kernel().worker.contains("BotPhenixAutoRevive"):
                Kernel().worker.removeFrameByName("BotPhenixAutoRevive")
            if BotConfig().path:
                if not Kernel().worker.contains("BotFarmPathFrame"):
                    Kernel().worker.addFrame(BotFarmPathFrame(True))
            return True

