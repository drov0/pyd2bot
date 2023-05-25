from typing import TYPE_CHECKING

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.AutoTrip import AutoTrip
from pyd2bot.logic.roleplay.behaviors.AutoTripUseZaap import AutoTripUseZaap
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.npc.NpcDialogReplyMessage import \
    NpcDialogReplyMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.npc.NpcGenericActionRequestMessage import \
    NpcGenericActionRequestMessage
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

if TYPE_CHECKING:
    pass

class NpcDialog(AbstractBehavior):
    NO_MORE_REPLIES = 10235
    
    def __init__(self) -> None:
        super().__init__()

    def run(self, npcMapId, npcId, npcOpenDialogId, npcQuestionsReplies) -> bool:
        self.npcMapId = npcMapId
        self.npcId = npcId
        self.npcOpenDialogId = npcOpenDialogId
        self.npcQuestionsReplies = npcQuestionsReplies
        self.currentNpcQuestionReplyIdx = 0
        self.dialogLeftListener = None
        AutoTripUseZaap().start(self.npcMapId, 1, callback=self.onNPCMapReached, parent=self)

    def onNpcQuestion(self, event, messageId, dialogParams, visibleReplies):
        if self.currentNpcQuestionReplyIdx == len(self.npcQuestionsReplies):
            return self.finish(self.NO_MORE_REPLIES, "Received an NPC question but have no more replies programmed")
        Logger().info(f"Received NPC question : {messageId}")
        msg = NpcDialogReplyMessage()
        msg.init(self.npcQuestionsReplies[self.currentNpcQuestionReplyIdx])
        self.currentNpcQuestionReplyIdx += 1
        KernelEventsManager().once(KernelEvent.NPC_QUESTION, self.onNpcQuestion, originator=self)
        ConnectionsHandler().send(msg)
    
    def onNpcDialogleft(self, event):
        self.finish(0, None)

    def onNPCMapReached(self, code, error):
        Logger().info(f"NPC Map reached with error : {error}")
        if error:
            return self.finish(code, error)
        msg = NpcGenericActionRequestMessage()
        msg.init(self.npcId, self.npcOpenDialogId, self.npcMapId)
        KernelEventsManager().once(KernelEvent.DIALOG_LEFT, self.onNpcDialogleft, originator=self)
        KernelEventsManager().once(KernelEvent.NPC_QUESTION, self.onNpcQuestion, originator=self)
        ConnectionsHandler().send(msg) 
