from pyd2bot.logic.managers.AccountManager import AccountManager
from pyd2bot.logic.managers.BotConfig import CharacterRoleEnum
from pyd2bot.Pyd2Bot import Pyd2Bot
from pyd2bot.thriftServer.pyd2botService.ttypes import (Session, SessionType,
                                                        UnloadType)

accountId = "244588168071629885"
character = AccountManager.get_character(accountId)
apikey = AccountManager.get_apikey(accountId)
bot = Pyd2Bot(character.login)
session = Session(
    id="test",
    leader=character,
    unloadType=UnloadType.BANK,
    type=SessionType.TREASURE_HUNT,
)
bot = Pyd2Bot(character.login)
bot.setConfig(apikey, session, CharacterRoleEnum.LEADER, character)
bot.start()
bot.join()