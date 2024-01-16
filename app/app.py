import os
from flask import Flask, render_template, jsonify
import json

from pyd2bot.logic.managers.AccountManager import AccountManager

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html', accounts=AccountManager.get_accounts())

@app.route('/run_command/<character_id>/<command>')
def run_command(character_id, command):
    # Implement the logic for the command (farm, treasurehunt, fight)
    return jsonify({"status": "success", "message": f"{command} command executed for {character_id}"})

if __name__ == '__main__':
    app.run(debug=True)
