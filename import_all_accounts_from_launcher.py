from pyd2bot.logic.managers.AccountManager import AccountManager
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

Logger().activateConsolLogging()
AccountManager.clear()
AccountManager.import_launcher_accounts()