import json
import os

from pydofus2.com.ankamagames.atouin.managers.MapDisplayManager import \
    MapDisplayManager
from pydofus2.com.ankamagames.dofus.datacenter.world.SubArea import SubArea
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.astar.AStar import \
    AStar
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.WorldGraph import \
    WorldGraph


class BankInfos:
    def __init__(
        self,
        npcActionId: int,
        npcId: float,
        npcMapId: float,
        openBankReplyId: int,
        name: str = "undefined",
    ):
        self.name = name
        self.npcActionId = npcActionId
        self.npcId = npcId
        self.npcMapId = npcMapId
        self.openBankReplyId = openBankReplyId

    def to_json(self):
        return {
            "npcActionId": self.npcActionId,
            "npcId": self.npcId,
            "npcMapId": self.npcMapId,
            "openBankReplyId": self.openBankReplyId,
        }


class Localizer:
    _phenixesByAreaId = dict[int, list]()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "areaInfos.json"), "r") as f:
        AREAINFOS: dict = json.load(f)
    with open(os.path.join(base_dir, "banks.json"), "r") as f:
        BANKS: dict = json.load(f)
        
    @classmethod
    def getBankInfos(cls) -> BankInfos:
        # subareaId = MapDisplayManager().currentDataMap.subareaId
        # subarea = SubArea.getSubAreaById(subareaId)
        # areaId = subarea._area.id
        # minDist = float("inf")
        # srcV = PlayedCharacterManager().currVertex
        # closestBankId = None
        # for bankId in cls.AREAINFOS[str(areaId)]["bank"]:
        #     bank = cls.BANKS[bankId]
        #     if bank["npcMapId"] == PlayedCharacterManager().currentMap.mapId:
        #         closestBankId = bankId
        #         break
        #     rpZ = 1
        #     while True:
        #         dstV = WorldGraph().getVertex(bank["npcMapId"], rpZ)
        #         if not dstV:
        #             break
        #         path = AStar().search(WorldGraph(), srcV, dstV)
        #         if path is not None:
        #             dist = len(path)
        #             if dist < minDist:
        #                 minDist = dist
        #                 closestBankId = bankId
        #             break
        #         rpZ += 1
        # if closestBankId is None:
        #     raise Exception(f"Could not find closest bank to areaId {areaId}")
        
        return BankInfos(**cls.BANKS["Astrub"])

    @classmethod
    def phenixMapId(cls) -> float:
        subareaId = MapDisplayManager().currentDataMap.subareaId
        subarea = SubArea.getSubAreaById(subareaId)
        areaId = subarea._area.id
        return cls.AREAINFOS[str(areaId)]["phoenix"]["mapId"]
