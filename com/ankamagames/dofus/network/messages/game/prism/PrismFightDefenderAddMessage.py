from com.ankamagames.dofus.network.messages.INetworkMessage import INetworkMessage
from com.ankamagames.dofus.network.types.game.character.CharacterMinimalPlusLookInformations import CharacterMinimalPlusLookInformations


class PrismFightDefenderAddMessage(INetworkMessage):
    protocolId = 58
    subAreaId:int
    fightId:int
    defender:CharacterMinimalPlusLookInformations
    
    
