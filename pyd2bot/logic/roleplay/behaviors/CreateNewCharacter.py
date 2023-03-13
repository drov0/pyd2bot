

from time import sleep
from typing import TYPE_CHECKING
from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.behaviors.UseSkill import UseSkill
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import KernelEvent, KernelEventsManager
from pydofus2.com.ankamagames.dofus.kernel.net.ConnectionsHandler import ConnectionsHandler
from pydofus2.com.ankamagames.dofus.logic.common.managers.PlayerManager import PlayerManager
from pydofus2.com.ankamagames.dofus.network.enums.CharacterCreationResultEnum import CharacterCreationResultEnum
from pydofus2.com.ankamagames.dofus.network.messages.game.character.choice.CharacterFirstSelectionMessage import CharacterFirstSelectionMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.character.creation.CharacterCreationRequestMessage import CharacterCreationRequestMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.character.creation.CharacterNameSuggestionRequestMessage import CharacterNameSuggestionRequestMessage
from pydofus2.com.ankamagames.dofus.network.messages.game.context.roleplay.quest.GuidedModeQuitRequestMessage import GuidedModeQuitRequestMessage
from pydofus2.com.ankamagames.jerakine.benchmark.BenchmarkTimer import BenchmarkTimer
from pydofus2.com.ankamagames.jerakine.data.I18n import I18n
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from enum import Enum
if TYPE_CHECKING:
    pass

class NewCharacterStates(Enum):
    GET_NAME_SUGGESTION = -1 
    CHARACTER_CREATION = 0
    CHARACTER_SELECTION = 1
    TUTORIAL = 2
    MOVING_TO_ASTRUB = 3
    OUT_OF_TUTORIAL = 4

class CreateNewCharacter(AbstractBehavior):

    def __init__(self) -> None:
        super().__init__()
        self.requestTimer = None

    def start(self, breedId, callback) -> bool:
        if self.running.is_set():
            return self.finish(False, "[CreateNewCharacter] Already running.")
        self.running.set()
        self.callback = callback
        self.name = None
        self.breedId = breedId
        self.sate = None
        self.nbrFails = 0
        self.charNameSuggListener = None
        self.charNameSuggFailListener = None
        Logger().info("[CreateNewCharacter] Started.")
        self.askNameSuggestion()

    def onCharacterNameSuggestion(self, event, suggestion):
        self.name = suggestion
        KernelEventsManager().remove_listener(KernelEvent.CHARACTER_NAME_SUGGESTION_FAILED, self.charNameSuggFailListener)
        self.requestNewCharacter()

    def onCharacterNameSuggestionFail(self, event):
        self.nbrFails += 1
        if self.nbrFails > 3:
            KernelEventsManager().remove_listener(KernelEvent.CHARACTER_NAME_SUGGESTION, self.charNameSuggListener)
            return self.finish(False, "failed to get character name suggestion")
        sleep(3)
        KernelEventsManager().once(KernelEvent.CHARACTER_NAME_SUGGESTION_FAILED, self.onCharacterNameSuggestionFail)
        msg = CharacterNameSuggestionRequestMessage()
        msg.init()
        ConnectionsHandler().send(msg)
    
    def askNameSuggestion(self):
        self.charNameSuggListener = KernelEventsManager().once(KernelEvent.CHARACTER_NAME_SUGGESTION, self.onCharacterNameSuggestion)
        self.charNameSuggFailListener = KernelEventsManager().once(KernelEvent.CHARACTER_NAME_SUGGESTION_FAILED, self.onCharacterNameSuggestionFail)
        msg = CharacterNameSuggestionRequestMessage()
        msg.init()
        ConnectionsHandler().send(msg)
        self.state = NewCharacterStates.GET_NAME_SUGGESTION

    def onNewCharacterResult(self, event, result, reason):
        if self.requestTimer:
            self.requestTimer.cancel()
        if result > 0:
            if result == CharacterCreationResultEnum.ERR_INVALID_NAME:
                errorMsg = I18n.getUiText("ui.charcrea.invalidNameReason" + str(reason))
            elif result == CharacterCreationResultEnum.ERR_NOT_ALLOWED:
                errorMsg = I18n.getUiText("ui.popup.charcrea.notSubscriber")
            elif result == CharacterCreationResultEnum.ERR_TOO_MANY_CHARACTERS:
                errorMsg = I18n.getUiText("ui.popup.charcrea.tooManyCharacters")
            elif result == CharacterCreationResultEnum.ERR_NO_REASON:
                errorMsg = I18n.getUiText("ui.popup.charcrea.noReason")
            elif result == CharacterCreationResultEnum.ERR_RESTRICTED_ZONE:
                errorMsg = I18n.getUiText("ui.charSel.deletionErrorUnsecureMode")
            self.finish(False, f"create character error : {errorMsg}")
        else:
            KernelEventsManager().once(KernelEvent.CHARACTERS_LIST, self.onCharacterList)

    def onMapProcessed(self):
        if self.state == NewCharacterStates.CHARACTER_SELECTION:
            KernelEventsManager().onceMapProcessed(self.onMapProcessed)
            def onquest(event, msg):
                msg = GuidedModeQuitRequestMessage()
                self.state = NewCharacterStates.TUTORIAL
                ConnectionsHandler().send(msg)
            KernelEventsManager().once(KernelEvent.QUEST_START, onquest)
        elif self.state == NewCharacterStates.TUTORIAL:
            KernelEventsManager().onceMapProcessed(self.onMapProcessed)
            self.state = NewCharacterStates.OUT_OF_TUTORIAL
        elif self.state == NewCharacterStates.OUT_OF_TUTORIAL:
            def onSkillUsed(status, error):
                if error:
                   return self.finish(status, error)
                KernelEventsManager().onceMapProcessed(lambda:self.finish(True, None), mapId=152046597)
            UseSkill().start(None, onSkillUsed, elementId=489318, skilluid=148931090, waitForSkillUsed=True)
        
    def onCharacterList(self, event, return_value):
        for ch in PlayerManager().charactersList:
            if ch.name == self.name: 
                KernelEventsManager().onceMapProcessed(self.onMapProcessed)
                msg = CharacterFirstSelectionMessage()
                msg.init(True, ch.id)
                ConnectionsHandler().send(msg)
                self.state = NewCharacterStates.CHARACTER_SELECTION
                return
        self.finish(False, "The created character is not found in characters list")                

    def requestNewCharacter(self):
        def onTimeout():
            self.finish(False, "Request character create timedout")
        KernelEventsManager().once(KernelEvent.CHARACTER_CRATION_RESULT, self.onNewCharacterResult)
        self.requestTimer = BenchmarkTimer(10, onTimeout)
        msg = CharacterCreationRequestMessage()
        msg.init(self.name, self.breedId, True, [12215600, 12111183, 4803893, 9083451, 13358995], 153)
        self.requestTimer.start()
        ConnectionsHandler().send(msg)
        self.state = NewCharacterStates.CHARACTER_CREATION
