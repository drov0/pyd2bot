from com.ankamagames.dofus.network.messages.INetworkMessage import INetworkMessage


class RecycledItem(INetworkMessage):
    protocolId = 161
    id:int
    qty:int
    
    