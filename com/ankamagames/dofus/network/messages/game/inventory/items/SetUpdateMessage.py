from com.ankamagames.jerakine.network.NetworkMessage import NetworkMessage
from com.ankamagames.dofus.network.types.game.data.items.effects.ObjectEffect import ObjectEffect


class SetUpdateMessage(NetworkMessage):
    setId:int
    setObjects:list[int]
    setEffects:list[ObjectEffect]
    
    
