

from pyd2bot.game.fight.context.GameContextActorPositionInformations import GameContextActorPositionInformations


class GameContextBasicSpawnInformation:
   teamId:int = 2
   alive:bool = False
   informations:GameContextActorPositionInformations
   
   def __init__(self):
      self.informations = GameContextActorPositionInformations()
      super().__init__()
   
   def getTypeId(self) -> int:
      return 2015
   
   def initGameContextBasicSpawnInformation(self, teamId:int = 2, alive:bool = False, informations:GameContextActorPositionInformations = None) -> 'GameContextBasicSpawnInformation':
      self.teamId = teamId
      self.alive = alive
      self.informations = informations
      return self
   
   def reset(self) -> None:
      self.teamId = 2
      self.alive = False
      self.informations = GameContextActorPositionInformations()
