import threading
from pyd2bot.misc.BotEventsmanager import BotEventsManager
from pyd2bot.logic.common.rpcMessages.BotConnectedMessage import BotConnectedMessage
from pyd2bot.logic.fight.frames.BotFightFrame import BotFightFrame
from pyd2bot.logic.fight.frames.BotMuleFightFrame import BotMuleFightFrame
from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.AutoRevive import AutoRevive
from pyd2bot.logic.roleplay.behaviors.FarmPath import FarmPath
from pyd2bot.logic.roleplay.behaviors.GiveItems import GiveItems
from pyd2bot.logic.roleplay.behaviors.UnloadInBank import UnloadInBank
from pyd2bot.logic.roleplay.frames.BotPartyFrame import BotPartyFrame
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import ConnectionsHandler
from pydofus2.com.ankamagames.dofus.kernel.net.PlayerDisconnectedMessage import PlayerDisconnectedMessage
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.logic.game.roleplay.frames.RoleplayEntitiesFrame import \
    RoleplayEntitiesFrame
from pydofus2.com.ankamagames.dofus.network.enums.GameContextEnum import \
    GameContextEnum
from pydofus2.com.ankamagames.dofus.network.enums.PlayerLifeStatusEnum import \
    PlayerLifeStatusEnum
from pydofus2.com.ankamagames.dofus.network.messages.common.basic.BasicPingMessage import BasicPingMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.GameContextCreateErrorMessage import GameContextCreateErrorMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.GameContextCreateMessage import \
    GameContextCreateMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.GameContextDestroyMessage import \
    GameContextDestroyMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.death.GameRolePlayGameOverMessage import \
    GameRolePlayGameOverMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.inventory.items.InventoryWeightMessage import InventoryWeightMessage
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.messages.Frame import Frame
from pydofus2.com.ankamagames.jerakine.messages.Message import Message
from pydofus2.com.ankamagames.jerakine.types.enums.Priority import Priority


class BotWorkflowFrame(Frame):
    def __init__(self):
        self.currentContext = None
        super().__init__()

    def pushed(self) -> bool:
        KernelEventsManager().on(KernelEvent.PLAYER_STATE_CHANGED, self.onPlayerStateChange, originator=self)
        KernelEventsManager().on(KernelEvent.TEXT_INFO, self.onServerNotif)
        self._delayedAutoUnlaod = False
        self.mapProcessedListeners = []
        return True

    def pulled(self) -> bool:
        KernelEventsManager().clearAllByOrigin(self)
        return True

    @property
    def priority(self) -> int:
        return Priority.VERY_LOW
    
    def process(self, msg: Message) -> bool:

        if isinstance(msg, GameContextCreateMessage):
            if self.currentContext is None:
                for instId, inst in Kernel.getInstances():
                    inst.worker.process(BotConnectedMessage(threading.current_thread().name))
            ctxname = "Fight" if msg.context == GameContextEnum.FIGHT else "Roleplay"
            Logger().separator(f"{ctxname} Game Context Created")
            self.currentContext = msg.context
            if BotConfig().party and not Kernel().worker.contains("BotPartyFrame"):
                Kernel().worker.addFrame(BotPartyFrame())
            if self.currentContext == GameContextEnum.ROLE_PLAY:
                if PlayedCharacterManager().inventoryWeightMax > 0 and PlayedCharacterManager().inventoryWeight / PlayedCharacterManager().inventoryWeightMax > 0.95:
                    Logger().warning(f"[BotWorkflow] Inventory is almost full will trigger auto unload ...")
                    return self.mapProcessedListeners.append(KernelEventsManager().onceMapProcessed(self.unloadInventory, originator=self))
                if BotConfig().path and not FarmPath().isRunning():
                    self.mapProcessedListeners.append(KernelEventsManager().onceMapProcessed(FarmPath().start, originator=self))
            elif self.currentContext == GameContextEnum.FIGHT:
                if BotConfig().isLeader:
                    Kernel().worker.addFrame(BotFightFrame())
                else:
                    Kernel().worker.addFrame(BotMuleFightFrame())
            return True

        elif isinstance(msg, InventoryWeightMessage):
            PlayedCharacterManager().inventoryWeight = msg.inventoryWeight
            PlayedCharacterManager().shopWeight = msg.shopWeight
            PlayedCharacterManager().inventoryWeightMax = msg.weightMax
            return True

        elif isinstance(msg, GameContextDestroyMessage):
            ctxname = "Fight" if self.currentContext == GameContextEnum.FIGHT else "Roleplay"
            Logger().separator(f"{ctxname} Context Destroyed")
            if self.currentContext == GameContextEnum.FIGHT:
                if BotConfig().isLeader and Kernel().worker.contains("BotFightFrame"):
                    Kernel().worker.removeFrameByName("BotFightFrame")
                elif Kernel().worker.contains("BotMuleFightFrame"):
                    Kernel().worker.removeFrameByName("BotMuleFightFrame")
            if self.currentContext == GameContextEnum.ROLE_PLAY:
                if BotConfig().path and FarmPath().isRunning():
                    FarmPath().stop()
            return True
        
        elif isinstance(msg, GameRolePlayGameOverMessage):
            self.onPlayerStateChange(None, PlayerLifeStatusEnum.STATUS_TOMBSTONE)
            return True
        
        elif isinstance(msg, GameContextCreateErrorMessage):
            KernelEventsManager().send(KernelEvent.RESTART, "Game context create Error")
            return True
        
        elif isinstance(msg, BotConnectedMessage):
            Logger().info(f"Bot {msg.instanceId} connected")
            BotEventsManager().send(BotEventsManager.BOT_CONNECTED, msg.instanceId)
            return True
        
        elif isinstance(msg, PlayerDisconnectedMessage):
            Logger().info(f"Bot {msg.instanceId} disconnected")
            BotEventsManager().send(BotEventsManager.BOT_DOSCONNECTED, msg.instanceId, msg.connectionType)
            return True
    
    def onPlayerStateChange(self, event, state):            
        PlayedCharacterManager().state = state
        if state == PlayerLifeStatusEnum.STATUS_TOMBSTONE or state == PlayerLifeStatusEnum.STATUS_PHANTOM:
            for listener in self.mapProcessedListeners:
                listener.delete()
            if BotConfig().isLeader:
                FarmPath().stop()
            if not PlayedCharacterManager().currentMap:
                return KernelEventsManager().onceMapProcessed(AutoRevive().start, [self.onPhenixAutoReviveEnded], originator=self)
            rpeframe: "RoleplayEntitiesFrame" = Kernel().worker.getFrameByName("RoleplayEntitiesFrame")
            if not rpeframe or not rpeframe.mcidm_processed:
                return KernelEventsManager().onceMapProcessed(AutoRevive().start, [self.onPhenixAutoReviveEnded], originator=self)
            AutoRevive().start(self.onPhenixAutoReviveEnded)
        
    def onPhenixAutoReviveEnded(self, status, error):
        if error:
            raise Exception(f"[BotWorkflow] Error while autoreviving player: {error}")
        if BotConfig().path and not FarmPath().isRunning():
            FarmPath().start()
        if BotConfig().party and not Kernel().worker.contains("BotPartyFrame"):
            Kernel().worker.addFrame(BotPartyFrame())
        return True

    def onServerNotif(self, event, msgId, msgType, textId, text):
        if textId == 5123:
            if not BotConfig().isSeller:
                KernelEventsManager().send(KernelEvent.RESTART, "Bot stayed inactive for too long, must have a bug")
            else:
                pingMsg = BasicPingMessage()
                pingMsg.init(True)
                ConnectionsHandler().send(pingMsg)
                
    def unloadInventory(self, callback=None):
        Logger().info("Unload inventory called")
        def onInventoryUnloaded(status, error):
            BotConfig.SELLER_VACANT.set()
            if BotConfig.SELLER_LOCK.locked():
                BotConfig.SELLER_LOCK.release()
            BotConfig().hasSellerLock = False
            if error:
                Logger().error(f"[BotWorkflow] Error while unloading inventory: {error}")
                return KernelEventsManager().send(KernelEvent.RESTART, f"[BotWorkflow] Error while unloading inventory: {error}")
            if BotConfig().party:
                Kernel().worker.addFrame(BotPartyFrame())
            if BotConfig().path and not FarmPath().isRunning():
                FarmPath().start()
            if callback:
                callback()
        if BotConfig().party:
            Kernel().worker.removeFrameByName("BotPartyFrame")
        if BotConfig().unloadInBank:
            UnloadInBank().start(onInventoryUnloaded)
        elif BotConfig().unloadInSeller:
            Logger().info("Aquiring seller lock")
            if not BotConfig.SELLER_VACANT.is_set():                
                Logger().info("Seller is busy, waiting for it to finish")
                BotConfig.SELLER_VACANT.wait()
                Logger().info("seller in vacant will try to ask for its services")
            if BotConfig.SELLER_LOCK.locked():
                Logger().info("Seller is already dealing with another client, waiting for it to be free")
            BotConfig.SELLER_LOCK.acquire()
            BotConfig().hasSellerLock = True
            BotConfig.SELLER_VACANT.clear()            
            Logger().info("seller lock aquired")
            GiveItems().start(BotConfig().seller, onInventoryUnloaded)
        if BotConfig().path and FarmPath().isRunning():
            FarmPath().stop()
    