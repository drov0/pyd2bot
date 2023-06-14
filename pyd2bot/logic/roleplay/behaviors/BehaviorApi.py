from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyd2bot.thriftServer.pyd2botService.ttypes import Character
    from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Edge import \
        Edge
    from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Transition import \
        Transition


class BehaviorApi: 
    
    def __init__(self) -> None:
        pass
        
    def autotripUseZaap(self, dstMapId, dstZoneId=1, withSaveZaap=False, callback=None):
        from pyd2bot.logic.roleplay.behaviors.movement.AutoTripUseZaap import \
            AutoTripUseZaap

        AutoTripUseZaap().start(dstMapId, dstZoneId, withSaveZaap, callback=callback, parent=self)
    
    def autoTrip(self, dstMapId, dstZoneId, path: list["Edge"]=None, callback=None):
        from pyd2bot.logic.roleplay.behaviors.movement.AutoTrip import AutoTrip

        AutoTrip().start(dstMapId, dstZoneId, path, callback=callback, parent=self)
    
    def changeMap(self, transition: "Transition"=None, edge: "Edge"=None, dstMapId=None, callback=None):
        from pyd2bot.logic.roleplay.behaviors.movement.ChangeMap import \
            ChangeMap

        ChangeMap().start(transition, edge, dstMapId, callback=callback, parent=self)
    
    def mapMove(self, destCell, exactDistination=True, callback=None):
        from pyd2bot.logic.roleplay.behaviors.movement.MapMove import MapMove

        MapMove().start(destCell, exactDistination, callback=callback, parent=self)
    
    def requestMapData(self, mapId=None, callback=None):
        from pyd2bot.logic.roleplay.behaviors.movement.RequestMapData import \
            RequestMapData

        RequestMapData().start(mapId, callback=callback, parent=self)
    
    def autoRevive(self, callback=None):
        from pyd2bot.logic.roleplay.behaviors.misc.AutoRevive import AutoRevive

        AutoRevive().start(callback=callback, parent=self)
    
    def attackMonsters(self, entityId, callback=None):
        from pyd2bot.logic.roleplay.behaviors.fight.AttackMonsters import \
            AttackMonsters

        AttackMonsters().start(entityId, callback=callback, parent=self)
    
    def farmFights(self, timeout=None, callback=None):
        from pyd2bot.logic.roleplay.behaviors.fight.FarmFights import \
            FarmFights

        FarmFights().start(timeout=timeout, callback=callback, parent=self)
        
    def muleFighter(self, leader: "Character", callback=None):
        from pyd2bot.logic.roleplay.behaviors.fight.MuleFighter import \
            MuleFighter

        MuleFighter().start(leader, callback=callback, parent=self)

    def SaveZaap(self, callback=None):
        from pyd2bot.logic.roleplay.behaviors.teleport.SaveZaap import SaveZaap

        SaveZaap().start(callback=callback, parent=self)

    def UseZaap(self, dstMapId, saveZaap=False, callback=None):
        from pyd2bot.logic.roleplay.behaviors.teleport.UseZaap import UseZaap

        UseZaap().start(dstMapId, saveZaap, callback=callback, parent=self)

    def UseSkill(self, ie, cell=None, exactDistination=False, waitForSkillUsed=True, elementId=None, skilluid=None, callback=None):
        from pyd2bot.logic.roleplay.behaviors.skill.UseSkill import UseSkill

        UseSkill().start(ie, cell, exactDistination, waitForSkillUsed, elementId, skilluid, callback=callback, parent=self)

    def SoloFarmFights(self, timeout=None, callback=None):
        from pyd2bot.logic.roleplay.behaviors.fight.SoloFarmFights import \
            SoloFarmFights

        SoloFarmFights().start(timeout=timeout, callback=callback, parent=self)

    def ResourceFarm(self, timeout=None, callback=None):
        from pyd2bot.logic.roleplay.behaviors.farm.ResourceFarm import \
            ResourceFarm

        ResourceFarm().start(timeout=timeout, callback=callback, parent=self)

    def PartyLeader(self, callback=None):
        from pyd2bot.logic.roleplay.behaviors.party.PartyLeader import \
            PartyLeader

        PartyLeader().start(callback=callback, parent=self)

    def WaitForMembersIdle(self, members, callback=None):
        from pyd2bot.logic.roleplay.behaviors.party.WaitForMembersIdle import \
            WaitForMembersIdle

        WaitForMembersIdle().start(members, callback=callback, parent=self)

    def WaitForMembersToShow(self, members, callback=None):
        from pyd2bot.logic.roleplay.behaviors.party.WaitForMembersToShow import \
            WaitForMembersToShow

        WaitForMembersToShow().start(members, callback=callback, parent=self)

    def NpcDialog(self, npcMapId, npcId, npcOpenDialogId, npcQuestionsReplies, callback=None):
        from pyd2bot.logic.roleplay.behaviors.npc.NpcDialog import NpcDialog

        NpcDialog().start(npcMapId, npcId, npcOpenDialogId, npcQuestionsReplies, callback=callback, parent=self)

    def GetOutOfAnkarnam(self, callback=None):
        from pyd2bot.logic.roleplay.behaviors.movement.GetOutOfAnkarnam import \
            GetOutOfAnkarnam

        GetOutOfAnkarnam().start(callback=callback, parent=self)

    def ChangeServer(self, newServerId, callback=None):
        from pyd2bot.logic.roleplay.behaviors.start.ChangeServer import \
            ChangeServer

        ChangeServer().start(newServerId, callback=callback, parent=self)

    def CreateNewCharacter(self, breedId, name=None, sex=False, callback=None):
        from pyd2bot.logic.roleplay.behaviors.start.CreateNewCharacter import \
            CreateNewCharacter

        CreateNewCharacter().start(breedId, name, sex, callback=callback, parent=self)

    def DeleteCharacter(self, characterId, callback=None):
        from pyd2bot.logic.roleplay.behaviors.start.DeleteCharacter import \
            DeleteCharacter

        DeleteCharacter().start(characterId, callback=callback, parent=self)

    def TreasureHunt(self, callback=None):
        from pyd2bot.logic.roleplay.behaviors.quest.ClassicTreasureHunt import \
            TreasureHunt

        TreasureHunt().start(callback=callback, parent=self)

    def BotExchange(self, direction, target, items=None, callback=None):
        from pyd2bot.logic.roleplay.behaviors.exchange.BotExchange import \
            BotExchange

        BotExchange().start(direction, target, items, callback=callback, parent=self)

    def OpenBank(self, bankInfos=None, callback=None):
        from pyd2bot.logic.roleplay.behaviors.bank.OpenBank import OpenBank

        OpenBank().start(bankInfos, callback=callback, parent=self)

    def RetrieveRecipeFromBank(self, recipe, return_to_start=True, bankInfos=None, callback=None):
        from pyd2bot.logic.roleplay.behaviors.bank.RetrieveRecipeFromBank import \
            RetrieveRecipeFromBank

        RetrieveRecipeFromBank().start(recipe, return_to_start, bankInfos, callback=callback, parent=self)

    def UnloadInBank(self, return_to_start=True, bankInfos=None, callback=None):
        from pyd2bot.logic.roleplay.behaviors.bank.UnloadInBank import \
            UnloadInBank

        UnloadInBank().start(return_to_start, bankInfos, callback=callback, parent=self)
