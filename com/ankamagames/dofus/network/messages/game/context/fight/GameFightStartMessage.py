from com.ankamagames.jerakine.network.NetworkMessage import NetworkMessage
from com.ankamagames.dofus.network.types.game.idol.Idol import Idol


class GameFightStartMessage(NetworkMessage):
    idols:list[Idol]
    
    
