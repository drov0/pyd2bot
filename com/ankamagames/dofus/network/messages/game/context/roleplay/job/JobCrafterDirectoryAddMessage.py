from com.ankamagames.jerakine.network.NetworkMessage import NetworkMessage
from com.ankamagames.dofus.network.types.game.context.roleplay.job.JobCrafterDirectoryListEntry import JobCrafterDirectoryListEntry


class JobCrafterDirectoryAddMessage(NetworkMessage):
    listEntry:JobCrafterDirectoryListEntry
    
    
