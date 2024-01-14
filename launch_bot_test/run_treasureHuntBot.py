import os
import sys

from PyQt5 import QtGui, QtWidgets

from pyd2bot.logic.managers.AccountManager import AccountManager
from pyd2bot.logic.managers.BotConfig import CharacterRoleEnum
from pyd2bot.Pyd2Bot import Pyd2Bot
from pyd2bot.thriftServer.pyd2botService.ttypes import (Session, SessionType,
                                                        UnloadType)

__dir__ = os.path.dirname(os.path.abspath(__file__))
class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    def __init__(self, icon, tooltip, parent=None):
        super(SystemTrayIcon, self).__init__(icon, parent)
        self.setToolTip(tooltip)
        
        menu = QtWidgets.QMenu(parent)
        exit_action = menu.addAction("Stop Bot")
        exit_action.triggered.connect(self.stop_bot)
        self.setContextMenu(menu)

    def stop_bot(self):
        print("Stopping the bot...")
        # Add your bot stopping logic here
        bot.shutdown()
        QtWidgets.QApplication.quit()
        

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
trayIcon = SystemTrayIcon(icon, character.login)
trayIcon.show()
sys.exit(app.exec_())
