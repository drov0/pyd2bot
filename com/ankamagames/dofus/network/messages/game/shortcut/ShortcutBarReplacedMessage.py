from com.ankamagames.jerakine.network.NetworkMessage import NetworkMessage
from com.ankamagames.dofus.network.types.game.shortcut.Shortcut import Shortcut


class ShortcutBarReplacedMessage(NetworkMessage):
    barType:int
    shortcut:Shortcut
    
    
