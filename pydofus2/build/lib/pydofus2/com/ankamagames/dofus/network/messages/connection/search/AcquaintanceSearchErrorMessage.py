from pydofus2.com.ankamagames.jerakine.network.NetworkMessage import NetworkMessage


class AcquaintanceSearchErrorMessage(NetworkMessage):
    reason:int
    

    def init(self, reason_:int):
        self.reason = reason_
        
        super().__init__()
    