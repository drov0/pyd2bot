from com.ankamagames.dofus.network.messages.INetworkMessage import INetworkMessage


class DungeonKeyRingMessage(INetworkMessage):
    protocolId = 6497
    availables:int
    unavailables:int
    
    
