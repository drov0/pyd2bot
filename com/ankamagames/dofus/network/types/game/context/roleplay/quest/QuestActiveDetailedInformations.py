from com.ankamagames.dofus.network.types.game.context.roleplay.quest.QuestActiveInformations import QuestActiveInformations
from com.ankamagames.dofus.network.types.game.context.roleplay.quest.QuestObjectiveInformations import QuestObjectiveInformations


class QuestActiveDetailedInformations(QuestActiveInformations):
    stepId:int
    objectives:list[QuestObjectiveInformations]
    
    
