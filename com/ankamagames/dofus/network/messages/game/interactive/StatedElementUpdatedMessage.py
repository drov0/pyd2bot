from com.ankamagames.dofus.network.messages.INetworkMessage import INetworkMessage
from com.ankamagames.dofus.network.types.game.interactive.StatedElement import StatedElement


class StatedElementUpdatedMessage(INetworkMessage):
    protocolId = 3961
    statedElement:StatedElement
    
    