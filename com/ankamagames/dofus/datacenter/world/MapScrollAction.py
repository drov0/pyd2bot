from com.ankamagames.dofus.types.IdAccessors import IdAccessors
from com.ankamagames.jerakine.data.GameData import GameData
from com.ankamagames.jerakine.interfaces.IDataCenter import IDataCenter


class MapScrollAction(IDataCenter):
      
      MODULE:str = "MapScrollActions"
      
      id:float
      
      rightExists:bool
      
      bottomExists:bool
      
      leftExists:bool
      
      topExists:bool
      
      rightMapId:float
      
      bottomMapId:float
      
      leftMapId:float
      
      topMapId:float
      
      def __init__(self):
         super().__init__()
      
      @staticmethod
      def getMapScrollActionById(self, id:float) -> 'MapScrollAction':
         return GameData.getobject(MapScrollAction.MODULE,id)
      
      @staticmethod
      def getMapScrollActions(self) -> list:
         return GameData.getobjects(MapScrollAction.MODULE)

      idAccessors:IdAccessors = IdAccessors(getMapScrollActionById,getMapScrollActions)
