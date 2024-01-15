from typing import TYPE_CHECKING

from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.movement.AutoTrip import AutoTrip
from pyd2bot.logic.roleplay.behaviors.movement.AutoTripUseZaap import \
    AutoTripUseZaap
from pydofus2.com.ankamagames.berilia.managers.KernelEvent import KernelEvent
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import \
    KernelEventsManager
from pydofus2.com.ankamagames.dofus.datacenter.npcs.Npc import Npc
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import \
    ConnectionsHandler
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.dofus.misc.utils.ParamsDecoder import \
    ParamsDecoder
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.npc.NpcDialogReplyMessage import \
    NpcDialogReplyMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.npc.NpcGenericActionRequestMessage import \
    NpcGenericActionRequestMessage
from pydofus2.com.ankamagames.jerakine.data.I18n import I18n
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.utils.pattern.PatternDecoder import \
    PatternDecoder

if TYPE_CHECKING:
    pass

class NpcDialog(AbstractBehavior):
    NO_MORE_REPLIES = 10235
    NO_PROGRAMMED_REPLY = 10236
    NOT_IN_MAP = 10237
    MISSING_CONDITION = 10238
    REPLAY_DOESNT_EXIST = 10239
    
    def __init__(self) -> None:
        super().__init__()

    def run(self, npcMapId, npcId, npcOpenDialogId, npcQuestionsReplies) -> bool:
        if PlayedCharacterManager().currentMap.mapId != npcMapId:
            return self.finish(self.NOT_IN_MAP, f"Character not in NPC map {npcMapId}")
        self.npcMapId = npcMapId
        self.npcId = npcId
        self.npcOpenDialogId = npcOpenDialogId
        self.npcQuestionsReplies = npcQuestionsReplies
        self.currentNpcQuestionReplyIdx = 0
        self.dialogLeftListener = None
        self.npc: Npc = None
        self._textParams = {}
        self._textParams["m"] = False;
        self._textParams["f"] = True;
        self._textParams["n"] = True;
        self._textParams["g"] = False;
        msg = NpcGenericActionRequestMessage()
        msg.init(self.npcId, self.npcOpenDialogId, self.npcMapId)
        self.once(KernelEvent.DialogLeft, self.onNpcDialogleft)
        self.once(KernelEvent.NpcQuestion, self.onNpcQuestion)
        self.on(KernelEvent.ServerTextInfo, self.onServerTextInfo)
        ConnectionsHandler().send(msg)
        
    def onServerTextInfo(self, event, msgId, msgType, textId, text, params):
        if textId == 309584: # The conditions for validating this response haven't been met.
            self.finish(self.MISSING_CONDITION, text)
            
    def getTextWithParams(textId:int, params:list, replace:str = "%") -> str:
        msgContent:str = I18n.getText(textId)
        if msgContent:
            return ParamsDecoder.applyParams(msgContent, params, replace)
        return ""
    
    def decodeText(str:str, params:list) -> str:
        return PatternDecoder.decode(str,params)
    
    def getTextFromkey(self, key, replace="%", *args):
        return I18n.getText(key, args, replace)
    
    def displayReplies(self, replies: list[int]):
        for rep in replies:
            for reply in self.npc.dialogReplies:
                replyId = int(reply[0])
                replyTextId = int(reply[1])
                if replyId == rep:
                    replyText = self.decodeText(self.getTextFromkey(replyTextId), self._textParams)
                    Logger().debug(f"Reply : {replyText}")
    
    def findReply(self, messageId:int, visibleReplies:list[int]) -> int:
        possibleReplies = self.npcQuestionsReplies.get(messageId)
        if not possibleReplies:
            possibleReplies = self.npcQuestionsReplies.get(-1) # wildcard
        for rep in possibleReplies:
            if rep in visibleReplies:
                return rep
        return None
    
    def onNpcQuestion(self, event, messageId, dialogParams, visibleReplies):
        replyId = self.findReply(messageId, visibleReplies)
        
        if not replyId:
            return self.finish(self.NO_PROGRAMMED_REPLY, f"Reply {self.npcQuestionsReplies[messageId]} not found in npc possible replies")
        
        Logger().info(f"Received NPC question : {messageId}")
        Logger().info(f"Visible replies : {visibleReplies}")
        self.npc = Npc.getNpcById(self.npcId)
        if self.npc:
            for msg in self.npc.dialogMessages:
                msgId = int(msg[0])
                msgTextId = int(msg[1])
                if msgId == messageId:
                    messagenpc = self.decodeText(self.getTextWithParams(msgTextId, dialogParams, "#"))
                    Logger().debug(f"Dialog message : {messagenpc}")
            self.displayReplies(visibleReplies)

        msg = NpcDialogReplyMessage()
        msg.init(replyId)
        self.currentNpcQuestionReplyIdx += 1
        self.once(KernelEvent.NpcQuestion, self.onNpcQuestion)
        ConnectionsHandler().send(msg)
    
    def onNpcDialogleft(self, event):
        self.finish(0, None)

