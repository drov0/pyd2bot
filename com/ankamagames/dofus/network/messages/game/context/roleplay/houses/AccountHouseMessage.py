from com.ankamagames.jerakine.network.NetworkMessage import NetworkMessage
from com.ankamagames.dofus.network.types.game.house.AccountHouseInformations import AccountHouseInformations


class AccountHouseMessage(NetworkMessage):
    houses:list[AccountHouseInformations]
    
    
