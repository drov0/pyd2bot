from com.ankamagames.dofus.network.messages.INetworkMessage import INetworkMessage


class RawDataMessage(INetworkMessage):
    protocolId = 6253
    content:bytearray
    
    