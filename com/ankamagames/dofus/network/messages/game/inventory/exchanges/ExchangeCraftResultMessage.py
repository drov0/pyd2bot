from com.ankamagames.dofus.network.messages.INetworkMessage import INetworkMessage


class ExchangeCraftResultMessage(INetworkMessage):
    protocolId = 8524
    craftResult:int
    
    
