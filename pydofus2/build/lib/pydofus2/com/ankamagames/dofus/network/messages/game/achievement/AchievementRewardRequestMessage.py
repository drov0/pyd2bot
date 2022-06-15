from pydofus2.com.ankamagames.jerakine.network.NetworkMessage import NetworkMessage


class AchievementRewardRequestMessage(NetworkMessage):
    achievementId:int
    

    def init(self, achievementId_:int):
        self.achievementId = achievementId_
        
        super().__init__()
    