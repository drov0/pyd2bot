from com.ankamagames.dofus.network.messages.INetworkMessage import INetworkMessage
from com.ankamagames.dofus.network.types.game.social.GuildVersatileInformations import GuildVersatileInformations


class GuildVersatileInfoListMessage(INetworkMessage):
    protocolId = 211
    guilds:GuildVersatileInformations
    
    