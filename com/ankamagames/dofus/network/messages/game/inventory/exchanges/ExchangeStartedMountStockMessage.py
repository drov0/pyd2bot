from com.ankamagames.jerakine.network.NetworkMessage import NetworkMessage
from com.ankamagames.dofus.network.types.game.data.items.ObjectItem import ObjectItem


class ExchangeStartedMountStockMessage(NetworkMessage):
    objectsInfos:list[ObjectItem]
    
    
