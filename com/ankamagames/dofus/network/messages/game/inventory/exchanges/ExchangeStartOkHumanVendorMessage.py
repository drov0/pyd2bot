from com.ankamagames.jerakine.network.NetworkMessage import NetworkMessage
from com.ankamagames.dofus.network.types.game.data.items.ObjectItemToSellInHumanVendorShop import ObjectItemToSellInHumanVendorShop


class ExchangeStartOkHumanVendorMessage(NetworkMessage):
    sellerId:int
    objectsInfos:list[ObjectItemToSellInHumanVendorShop]
    
    
