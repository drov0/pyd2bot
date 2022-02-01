from com.ankamagames.dofus.network.types.game.friend.AbstractContactInformations import AbstractContactInformations


class LeagueFriendInformations(AbstractContactInformations):
    playerId:int
    playerName:str
    breed:int
    sex:bool
    level:int
    leagueId:int
    totalLeaguePoints:int
    ladderPosition:int
    
    
