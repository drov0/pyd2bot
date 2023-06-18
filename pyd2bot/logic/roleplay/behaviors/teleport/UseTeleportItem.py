from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.dofus.internalDatacenter.items.ItemWrapper import \
    ItemWrapper
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel


class UseTeleportItem(AbstractBehavior):
    CANT_USE_ITEM_IN_MAP = 478886

    def __init__(self) -> None:
        super().__init__()

    def run(self, iw: ItemWrapper):
        self.onceMapProcessed(
            lambda: self.finish(True, None)
        )
        Kernel().inventoryManagementFrame.useItem(iw)
        self.onNewMap(True, None)
        
    def onServerInfo(self, event, msgId, msgType, textId, msgContent, params):
        if textId == 4641:
            return self.finish(self.CANT_USE_ITEM_IN_MAP, f"Cant use this teleport item on this map")

    def onNewMap(self, code, err):
        if err:
            return self.finish(code, err)
    
