from com.ankamagames.dofus.network.messages.INetworkMessage import INetworkMessage
from com.ankamagames.dofus.network.types.game.data.items.ObjectItem import ObjectItem


class ObjectsAddedMessage(INetworkMessage):
    protocolId = 1568
    object:ObjectItem
    
    