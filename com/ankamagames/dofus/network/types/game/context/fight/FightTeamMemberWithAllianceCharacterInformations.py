from com.ankamagames.dofus.network.types.game.context.fight.FightTeamMemberCharacterInformations import FightTeamMemberCharacterInformations
from com.ankamagames.dofus.network.types.game.context.roleplay.BasicAllianceInformations import BasicAllianceInformations


class FightTeamMemberWithAllianceCharacterInformations(FightTeamMemberCharacterInformations):
    protocolId = 2689
    allianceInfos:BasicAllianceInformations
    
    