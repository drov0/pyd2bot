from com.ankamagames.dofus.network.messages.INetworkMessage import INetworkMessage


class GameFightSpellCooldown(INetworkMessage):
    protocolId = 5389
    spellId:int
    cooldown:int
    
    
