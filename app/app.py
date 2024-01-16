import json
import os
import time

from flask import Flask, jsonify, render_template
from launch_bot_test.run_treasureHuntBot import run_treasureHuntBot

from pyd2bot.logic.managers.AccountManager import AccountManager
from pyd2bot.thriftServer.pyd2botService.ttypes import SessionStatus
from pydofus2.com.ankamagames.dofus.kernel.net.DisconnectionReasonEnum import \
    DisconnectionReasonEnum
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger


def format_runtime(startTime):
    seconds = time.time() - startTime
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    if hours == 0:
        if minutes == 0:
            result = f"{int(seconds)}s"
        else:
            result = f"{int(minutes)}m {int(seconds)}s"
    else:
        result = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    return result

def tail(filename, n=300):
    with open(filename, 'r', encoding='ISO-8859-1') as file:
        lines = file.readlines()
        return ''.join(lines[-n:])

class BotManagerApp:
    def __init__(self):
        self.app = Flask(__name__)
        self._running_bots = dict()
        self.setup_routes()

    def setup_routes(self):
        @self.app.route("/")
        def index():
            return render_template(
                "index.html", accounts=AccountManager.get_accounts(), runningBots=self._running_bots.values()
            )

        @self.app.route("/run/<account_id>/<character_id>/<action>")
        def run_action(account_id, character_id, action):
            if action == "treasurehunt":
                accountkey = AccountManager.get_accountkey(account_id)
                character = AccountManager.get_character(accountkey, character_id)
                bot = run_treasureHuntBot(self.on_bot_shutdown, accountkey, character_id)
                self._running_bots[account_id] = {"obj": bot, "startTime": time.time(), "character": character.name, "activity": action}
            return jsonify(
                {
                    "status": "success",
                    "message": f"Running {action} for account {account_id}, character {character_id}",
                }
            )

        @self.app.route("/stop/<account_id>/<character_id>")
        def stop_action(account_id, character_id):
            bot_data = self._running_bots.get(account_id)
            if bot_data:
                bot = bot_data["obj"]
                bot.shutdown(DisconnectionReasonEnum.WANTED_SHUTDOWN, "User wanted to stop bot")
            return jsonify({"status": "success", "message": f"Stopped account {account_id}, character {character_id}"})

        @self.app.route("/get_running_bots")
        def get_running_bots():
            return jsonify(
                [
                    {
                        "name": bot["obj"].name,
                        "character": bot["character"],
                        "runTime": format_runtime(bot["startTime"]),
                        "status": SessionStatus._VALUES_TO_NAMES[bot["obj"].getState()],
                        "activity": bot["activity"],
                    }
                    for bot in self._running_bots.values()
                ]
            )

        @self.app.route("/get_log/<name>")
        def get_log(name):
            filep = Logger.getInstance(name).outputFile
            log_data = tail(filep, 500)
            return log_data, 200, {'Content-Type': 'text/plain'}
        
    def on_bot_shutdown(self, message, reason):
        print(f"Bot shutdown: {message} - {reason}")

    def run(self, debug=True):
        self.app.run(debug=debug)


if __name__ == "__main__":
    bot_manager_app = BotManagerApp()
    bot_manager_app.run(debug=True)
