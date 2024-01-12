import json
import os
import threading

from pyd2bot.logic.managers.AccountManager import AccountManager

game = 1 # 1 = Dofus
apikey = 'your_api_key'
account_data = AccountManager.fetch_account(game, apikey)
print(account_data)