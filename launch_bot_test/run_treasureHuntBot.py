import os
import sys

from launch_bot_test.system_tray import SystemTrayIcon
from PyQt5 import QtGui, QtWidgets

from pyd2bot.logic.managers.AccountManager import AccountManager
from pyd2bot.logic.managers.BotConfig import CharacterRoleEnum
from pyd2bot.Pyd2Bot import Pyd2Bot
from pyd2bot.thriftServer.pyd2botService.ttypes import (Session, SessionType,
                                                        UnloadType)

__dir__ = os.path.dirname(os.path.abspath(__file__))

def run_treasureHuntBot(callback, account_key, characterId=None) -> Pyd2Bot:
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    character = AccountManager.get_character(account_key, characterId)
    apikey = AccountManager.get_apikey(account_key)
    bot = Pyd2Bot(character.login)
    session = Session(
        id="test",
        leader=character,
        unloadType=UnloadType.BANK,
        type=SessionType.TREASURE_HUNT,
    )
    bot.setConfig(apikey, session, CharacterRoleEnum.LEADER, character)
    bot.start()
    bot.addShutDownListener(callback)
    icon = QtGui.QIcon(os.path.join(__dir__, "icon.png"))
    trayIcon = SystemTrayIcon(icon, bot)
    trayIcon.show()
    return bot
