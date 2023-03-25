from typing import TYPE_CHECKING

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.AutoTrip import AutoTrip
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

    def __init__(self) -> None:
        super().__init__()

    def run(self, npcMapId, npcId, npcOpenDialogId, npcQuestionsReplies) -> bool:
        self.npcMapId = npcMapId
        self.npcId = npcId
        self.npcOpenDialogId = npcOpenDialogId
        self.npcQuestionsReplies = npcQuestionsReplies
        self.currentNpcQuestionReplyIdx = 0
        self.dialogLeftListener = None
        Logger().info("[NpcDialog] Started.")
        AutoTrip().start(self.npcMapId, 1, callback=self.onNPCMapReached, parent=self)

    def onNpcQuestion(self, event, messageId, dialogParams, visibleReplies):
        if self.currentNpcQuestionReplyIdx == len(self.npcQuestionsReplies):
            KernelEventsManager().remove_listener(KernelEvent.NPC_DIALOG_LEFT, self.dialogLeftListener)
            return self.finish(False, "[NpcDialog] Received an npc question but have no more replies programmed")
        msg = NpcDialogReplyMessage()
        msg.init(self.npcQuestionsReplies[self.currentNpcQuestionReplyIdx])
        self.currentNpcQuestionReplyIdx += 1
        KernelEventsManager().once(KernelEvent.NPC_QUESTION, self.onNpcQuestion, originator=self)
        ConnectionsHandler().send(msg)
    
    def onNpcDialogleft(self, event):
        self.finish(True, None)

    def onNPCMapReached(self, status, error):
        if error:
            return self.finish(status, f"Move to npc Map failed with error : {error}")
        msg = NpcGenericActionRequestMessage()
        msg.init(self.npcId, self.npcOpenDialogId, self.npcMapId)
        self.dialogLeftListener = KernelEventsManager().once(KernelEvent.NPC_DIALOG_LEFT, self.onNpcDialogleft, originator=self)
        KernelEventsManager().once(KernelEvent.NPC_QUESTION, self.onNpcQuestion, originator=self)
        ConnectionsHandler().send(msg) 
