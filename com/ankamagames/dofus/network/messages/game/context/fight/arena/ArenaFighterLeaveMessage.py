from com.ankamagames.dofus.network.messages.INetworkMessage import INetworkMessage
from com.ankamagames.dofus.network.types.game.character.CharacterBasicMinimalInformations import CharacterBasicMinimalInformations


class ArenaFighterLeaveMessage(INetworkMessage):
    protocolId = 1880
    leaver:CharacterBasicMinimalInformations
    
    