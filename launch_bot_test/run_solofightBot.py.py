from pyd2bot.logic.managers.AccountManager import AccountManager
from pyd2bot.Pyd2Bot import Pyd2Bot
from pyd2bot.thriftServer.pyd2botService.ttypes import (
    Path,
    PathType,
    Session,
    SessionType,
    UnloadType,
    Vertex,
    TransitionType,
)


# ankarnam 154010883
# village astrub 191106048
# ankama coin bouftou 88082704
# Lac cania - pleines rocheuses : 156240386

if __name__ == "_main__":
    account_key = "244588168071629885"
    character = AccountManager.get_character(account_key)
    apikey = AccountManager.get_apikey(account_key)
    cert = AccountManager.get_cert(account_key)
    session = Session(
        id="test_fight_solo",
        character=character,
        unloadType=UnloadType.BANK,
        type=SessionType.FIGHT,
        path=Path(
            id="test_path",
            type=PathType.RandomSubAreaFarmPath,
            startVertex=Vertex(mapId=154010883.0, zoneId=1),
            transitionTypeWhitelist=[TransitionType.SCROLL, TransitionType.SCROLL_ACTION],
        ),
        monsterLvlCoefDiff=1.4,
        apikey=apikey,
        cert=cert,
    )
    bot = Pyd2Bot(session)
    bot.start()
    bot.join()
