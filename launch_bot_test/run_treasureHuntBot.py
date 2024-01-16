import os
import sys

from PyQt5 import QtGui, QtWidgets
from launch_bot_test.system_tray import SystemTrayIcon

from pyd2bot.logic.managers.AccountManager import AccountManager
from pyd2bot.logic.managers.BotConfig import CharacterRoleEnum
from pyd2bot.Pyd2Bot import Pyd2Bot
from pyd2bot.thriftServer.pyd2botService.ttypes import (Session, SessionType,
                                                        UnloadType)

__dir__ = os.path.dirname(os.path.abspath(__file__))

app = QtWidgets.QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

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
bot.setConfig(apikey, session, CharacterRoleEnum.LEADER, character)
bot.start()
bot.addShutDownListener(lambda: QtWidgets.QApplication.quit())

# Setting up the system tray icon
icon = QtGui.QIcon(os.path.join(__dir__, "icon.png"))
trayIcon = SystemTrayIcon(icon, bot)
trayIcon.show()
sys.exit(app.exec_())