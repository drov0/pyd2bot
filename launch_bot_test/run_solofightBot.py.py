from pyd2bot.logic.managers.AccountManager import AccountManager
from pyd2bot.logic.managers.BotConfig import CharacterRoleEnum
from pyd2bot.logic.roleplay.behaviors.farm.ResourceFarm import ResourceFarm
from pyd2bot.Pyd2Bot import Pyd2Bot
from pyd2bot.thriftServer.pyd2botService.ttypes import (JobFilter, Path,
                                                        PathType, Session,
                                                        SessionType,
                                                        UnloadType, Vertex, TransitionType)
from pydofus2.com.ankamagames.dofus.kernel.net.DisconnectionReasonEnum import \
    DisconnectionReasonEnum
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

# ankarnam 154010883
# village astrub 191106048
# ankama coin bouftou 88082704
# Lac cania - pleines rocheuses : 156240386

if __name__ == "__main__":    
    path = Path(
        id="test_path",
        type=PathType.RandomSubAreaFarmPath,
        startVertex=Vertex(
            mapId=191106048.0, 
            zoneId=1
        ),
        transitionTypeWhitelist=[TransitionType.SCROLL, TransitionType.SCROLL_ACTION]
    )
    accountId = "244588168071629885"
    character = AccountManager.get_character(accountId)
    apikey = AccountManager.get_apikey(accountId)
    bot = Pyd2Bot(character.login)

    def onShutDown():
        Logger().warning(f"Character {character.login} shutdowned.")
        bot.shutdown(DisconnectionReasonEnum.WANTED_SHUTDOWN, f"Character {character.login} shutdowned")

    bot.addShutDownListener(onShutDown)
    
    session = Session(
        id="test",
        leader=character,
        unloadType=UnloadType.BANK,
        type=SessionType.FIGHT,
        path=path,
        monsterLvlCoefDiff=1.7
    )
    
    bot = Pyd2Bot(character.login)
    bot.setConfig(apikey, session, CharacterRoleEnum.LEADER, character)
    bot.start()
    bot.join()
    