from com.ankamagames.jerakine.network.NetworkMessage import NetworkMessage
from com.ankamagames.dofus.network.types.game.character.debt.DebtInformation import DebtInformation


class DebtsUpdateMessage(NetworkMessage):
    action:int
    debts:list[DebtInformation]
    
    
