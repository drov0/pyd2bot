from com.ankamagames.dofus.network.messages.INetworkMessage import INetworkMessage


class IconPresetSaveRequestMessage(INetworkMessage):
    protocolId = 4898
    presetId:int
    symbolId:int
    updateData:bool
    
    