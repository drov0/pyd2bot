from com.ankamagames.dofus.network.messages.INetworkMessage import INetworkMessage


class GameServerInformations(INetworkMessage):
    protocolId = 5238
    id:int
    type:int
    status:int
    completion:int
    charactersCount:int
    charactersSlots:int
    date:int
    isMonoAccount:bool
    isSelectable:bool
    
    
