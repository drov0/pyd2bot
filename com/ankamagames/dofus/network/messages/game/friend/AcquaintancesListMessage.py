from com.ankamagames.dofus.network.messages.INetworkMessage import INetworkMessage
from com.ankamagames.dofus.network.types.game.friend.AcquaintanceInformation import AcquaintanceInformation


class AcquaintancesListMessage(INetworkMessage):
    protocolId = 2842
    acquaintanceList:AcquaintanceInformation
    
    