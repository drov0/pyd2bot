from com.ankamagames.dofus.network.messages.INetworkMessage import INetworkMessage


class BreachRoomUnlockResultMessage(INetworkMessage):
    protocolId = 3212
    roomId:int
    result:int
    
    