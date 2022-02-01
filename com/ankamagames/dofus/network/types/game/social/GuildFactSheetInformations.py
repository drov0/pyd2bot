from com.ankamagames.dofus.network.types.game.context.roleplay.GuildInformations import GuildInformations
from com.ankamagames.dofus.network.types.game.guild.recruitment.GuildRecruitmentInformation import GuildRecruitmentInformation


class GuildFactSheetInformations(GuildInformations):
    leaderId:int
    nbMembers:int
    lastActivityDay:int
    recruitment:GuildRecruitmentInformation
    nbPendingApply:int
    
    
