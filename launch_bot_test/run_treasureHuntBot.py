from pyd2bot.logic.managers.AccountManager import AccountManager
from pyd2bot.logic.managers.BotConfig import CharacterRoleEnum
from pyd2bot.Pyd2Bot import Pyd2Bot
from pyd2bot.thriftServer.pyd2botService.ttypes import (Session, SessionType,
                                                        UnloadType)
from pydofus2.com.ankamagames.dofus.kernel.net.DisconnectionReasonEnum import \
    DisconnectionReasonEnum
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

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

def onShutDown():
    Logger().warning(f"Character '{character.login}' shutdowned.")
    bot.shutdown(DisconnectionReasonEnum.WANTED_SHUTDOWN, f"Character '{character.login}' shutdowned.")
    
bot.addShutDownListener(onShutDown)
bot.setConfig(apikey, session, CharacterRoleEnum.LEADER, character)
bot.start()
bot.join()