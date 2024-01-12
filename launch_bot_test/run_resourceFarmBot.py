from pyd2bot.logic.managers.AccountManager import AccountManager
from pyd2bot.logic.managers.BotConfig import CharacterRoleEnum
from pyd2bot.logic.roleplay.behaviors.farm.ResourceFarm import ResourceFarm
from pyd2bot.Pyd2Bot import Pyd2Bot
from pyd2bot.thriftServer.pyd2botService.ttypes import (JobFilter, Path,
                                                        PathType, Session,
                                                        SessionType,
                                                        UnloadType, Vertex)
from pydofus2.com.ankamagames.dofus.kernel.net.DisconnectionReasonEnum import \
    DisconnectionReasonEnum
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

# ankarnam 154010883
# village astrub 191106048
# ankama coin bouftou 88082704
# Lac cania - pleines rocheuses : 156240386

if __name__ == "__main__":
    accountId = "244588168071629885"
    
    path = Path(
        id="test_path",
        type=PathType.RandomAreaFarmPath,
        startVertex=Vertex(
            mapId=154010883.0, 
            zoneId=1
        )
    )
    accountId = accountId
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
        type=SessionType.FARM,
        path=path,
        jobFilters = [
            JobFilter(36, []), # Pêcheur goujon
            JobFilter(2, []), # Bucheron,
            JobFilter(26, []), # Alchimiste
            JobFilter(28, []), # Paysan
            JobFilter(1, [311]), # Base : eau
            JobFilter(24, []) # Miner
        ]
    )
    bot = Pyd2Bot(character.login)
    bot.setConfig(apikey, session, CharacterRoleEnum.LEADER, character)
    bot.start()
    ResourceFarm.WaitThreadRegister(character.login, 60 * 10)
    bot.join()
    print(f"Character '{character.login}' shutdowned.")
    