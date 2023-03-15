from pyd2bot.logic.common.frames.BotCharacterUpdatesFrame import BotCharacterUpdatesFrame
from pyd2bot.logic.common.frames.BotRPCFrame import BotRPCFrame
from pyd2bot.logic.common.frames.BotWorkflowFrame import BotWorkflowFrame
from pyd2bot.logic.managers.BotConfig import BotConfig, CharacterRoleEnum
from pyd2bot.logic.roleplay.behaviors.AbstractBehavior import AbstractBehavior
from pyd2bot.logic.roleplay.frames.BotPartyFrame import BotPartyFrame
from pyd2bot.thriftServer.pyd2botService.ttypes import Character, Session
from pydofus2.com.DofusClient import DofusClient


class Pyd2Bot(DofusClient):
    def __init__(self, name="unknown"):
        super().__init__(name)

    def setConfig(
        self,
        apiKey: str,
        certId: int,
        certHash: str,
        session: Session,
        role: CharacterRoleEnum,
        character: Character,
    ):
        self._apiKey = apiKey
        self._certId = certId
        self._certHash = certHash
        self._session = session
        self._role = role
        self._character = character
        self._serverId = character.serverId
        self._characterId = character.id
        self.mule = role != CharacterRoleEnum.LEADER

    def onRestart(self, event, mesg):
        if BotConfig().hasSellerLock:
            BotConfig().releaseSellerLock()
        AbstractBehavior.clearAllChilds()
        return super().onRestart(event, mesg)
    
    def onInGame(self, event, msg):
        if self._role == CharacterRoleEnum.SELLER:
            BotConfig.SELLER_VACANT.set()

    def run(self):
        BotConfig().initFromSession(self._session, self._role, self._character)
        self.registerInitFrame(BotWorkflowFrame)
        self.registerInitFrame(BotRPCFrame)
        if BotConfig().party:
            self.registerInitFrame(BotPartyFrame)
        self.registerGameStartFrame(BotCharacterUpdatesFrame)
        return super().run()
