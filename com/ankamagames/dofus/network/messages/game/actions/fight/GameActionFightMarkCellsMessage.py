from com.ankamagames.dofus.network.messages.game.actions.AbstractGameActionMessage import AbstractGameActionMessage
from com.ankamagames.dofus.network.types.game.actions.fight.GameActionMark import GameActionMark


class GameActionFightMarkCellsMessage(AbstractGameActionMessage):
    mark:GameActionMark
    
    
