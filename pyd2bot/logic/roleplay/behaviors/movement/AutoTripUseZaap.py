from typing import Tuple

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.movement.AutoTrip import AutoTrip
from pyd2bot.logic.roleplay.behaviors.teleport.UseZaap import UseZaap
from pyd2bot.misc.Localizer import Localizer
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.dofus.datacenter.world.MapPosition import MapPosition
from pydofus2.com.ankamagames.dofus.datacenter.world.SubArea import SubArea
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.common.managers.PlayerManager import \
    PlayerManager
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.astar.AStar import \
    AStar
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Vertex import \
    Vertex
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.WorldGraph import \
    WorldGraph
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


class AutoTripUseZaap(AbstractBehavior):
    NOASSOCIATED_ZAAP = 996555
    BOT_BUSY = 8877444
    ZAAP_HINT_CAREGORY = 9

    _allZaapMapIds: list[int] = None

    def __init__(self) -> None:
        self.srcZaapVertex = None
        super().__init__()

    def run(self, dstMapId, dstZoneId=1, withSaveZaap=False, maxCost=float("inf")):
        if not dstMapId:
            raise ValueError(f"Invalid MapId value {dstMapId}!")
        self.maxCost = maxCost
        self.dstMapId = dstMapId
        self.dstZoneId = dstZoneId
        self.withSaveZaap = withSaveZaap
        self.on(KernelEvent.ServerTextInfo, self.onServerInfo)
        self.dstZaapMapId = Localizer.findCloseZaapMapId(dstMapId, maxCost)
        if not self.dstZaapMapId:
            Logger().warning(f"No associated zaap found for map {dstMapId}")
            return self.autoTrip(self.dstMapId, self.dstZoneId, callback=self.finish)
        self.havreSacMapListener = None
        if not PlayedCharacterManager().isZaapKnown(self.dstZaapMapId):
            Logger().debug(
                f"Dest zaap at map {self.dstZaapMapId} is not known -> will travel to register it."
            )
            return self.autoTrip(self.dstZaapMapId, self.dstZoneId, callback=self.onDstZaapTrip)
        self.dstVertex = WorldGraph().getVertex(self.dstMapId, self.dstZoneId)
        self.dstZaapVertex, self.dstZaapDist = self.findDistFrom(self.dstVertex, self.dstZaapMapId)
        Logger().debug(f"Dest Zaap is at '{self.dstZaapDist}' steps from dest Map.")
        if PlayerManager().isBasicAccount():
            self.srcZaapMapId = Localizer.findCloseZaapMapId(PlayedCharacterManager().currentMap.mapId, maxCost)
            if not self.srcZaapMapId:
                return self.finish(self.NOASSOCIATED_ZAAP, f"No associated Zaap found for map '{self.srcZaapMapId}'.")
            self.srcZaapVertex, self.srcZaapDist = self.findDistFrom(
                PlayedCharacterManager().currVertex, self.srcZaapMapId
            )
            Logger().debug(f"Src Zaap is at '{self.srcZaapDist}' steps from current Map.")
        else:
            self.srcZaapDist = 0
        self.dstVertex, self.distFromTarget = self.findDistFrom(
            PlayedCharacterManager().currVertex, dstMapId, maxLen=self.srcZaapDist + self.dstZaapDist
        )
        if self.distFromTarget == float("inf"):
            Logger().debug("Its more worth to take zaaps than to walk to dest map")
        else:
            Logger().debug(f"Dest Map is at '{self.distFromTarget}' steps.")
        if self.distFromTarget <= self.srcZaapDist + self.dstZaapDist:
            self.autoTrip(self.dstVertex.mapId, self.dstVertex.zoneId, callback=self.finish)
        elif PlayerManager().isBasicAccount():
            self.autoTrip(self.srcZaapVertex.mapId, self.srcZaapVertex.zoneId, callback=self.onSrcZaapTrip)
        else:
            self.enterHavreSac(self.onSrcZaapTrip)

    def enterHavreSac(self, callback):
        self.havreSacMapListener = self.onceMapProcessed(
            callback=callback,
        )
        return Kernel().roleplayContextFrame.havenbagEnter()

    def onServerInfo(self, event, msgId, msgType, textId, msgContent, params):
        if textId == 589088:  # Can't join havresac from current Map
            if self.havreSacMapListener:
                self.havreSacMapListener.delete()
            if not self.srcZaapVertex:
                self.srcZaapMapId = Localizer.findCloseZaapMapId(PlayedCharacterManager().currentMap.mapId, self.maxCost)
                if not self.srcZaapMapId:
                    return self.finish(
                        self.NOASSOCIATED_ZAAP, f"No associated Zaap found for map '{self.srcZaapMapId}'."
                    )
                self.srcZaapVertex, self.srcZaapDist = self.findDistFrom(
                    PlayedCharacterManager().currVertex, self.srcZaapMapId
                )
                Logger().debug(f"Src Zaap is at '{self.srcZaapDist}' steps from current Map.")
            self.autoTrip(self.srcZaapVertex.mapId, self.srcZaapVertex.zoneId, callback=self.onSrcZaapTrip)
        elif textId == 592304:  # le bot est occupé
            self.finish(self.BOT_BUSY, "Bot is busy so cant use zaap and walking might raise unexpected errors.")

    def onDstZaapTrip(self, code, err):
        if err:
            if code == UseZaap.NOT_RICH_ENOUGH:
                Logger().warning(err)
                if PlayerManager().isMapInHavenbag(PlayedCharacterManager().currentMap.mapId):
                    return self.enterHavreSac(
                        lambda: self.autoTrip(self.dstMapId, self.dstZoneId, callback=self.finish)
                    )
                else:
                    return self.autoTrip(self.dstMapId, self.dstZoneId, callback=self.finish)
            elif code == AutoTrip.NO_PATH_FOUND:
                Logger().warning("No path found to dest zaap will travel to dest map on feet")
                return self.autoTrip(self.dstMapId, self.dstZoneId, callback=self.finish)
        else:
            self.autoTrip(self.dstMapId, self.dstZoneId, callback=self.finish)

    def onSrcZaapTrip(self, code=1, err=None):
        if err:
            return self.finish(code, err)
        if not PlayedCharacterManager().currentMap:
            return self.onceMapProcessed(lambda: self.onSrcZaapTrip(code, err))
        if self.dstZaapVertex.mapId == PlayedCharacterManager().currentMap.mapId:
            self.onDstZaapTrip(True, None)
        else:
            self.useZaap(self.dstZaapVertex.mapId, callback=self.onDstZaapTrip, saveZaap=self.withSaveZaap)

    @classmethod
    def findDistFrom(cls, srcV: Vertex, mapId, maxLen=float("inf")) -> Tuple[Vertex, int]:
        if srcV is None:
            None, None
        if mapId == srcV.mapId:
            return srcV, 0
        rpZ = 1
        minDist = float("inf")
        vertex = None
        while True:
            dstV = WorldGraph().getVertex(mapId, rpZ)
            if not dstV:
                break
            path = AStar().search(WorldGraph(), srcV, dstV, maxPathLength=min(maxLen, minDist))
            if path is not None:
                dist = len(path)
                if dist < minDist:
                    minDist = dist
                    vertex = dstV
            rpZ += 1
        return vertex, minDist
