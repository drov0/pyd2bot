# pyd2bot
A bot that uses pydofus2 as a background client

## Prerequisites:
- Install of python 3.9.11 (other versions might work, not guaranteed)
- Install pcap and shark for sniffer functionality

## Steps for developers:
1. Create a new folder, e.g., 'botdev', `cd botdev`
2. Clone pydofus2: `git clone https://github.com/kmajdoub/pydofus2.git`
3. Clone pyd2bot: `git clone https://github.com/kmajdoub/pyd2bot.git`
4. Create a new venv in folder `python -m venv .venv`
5. Extract path to pydofus2 and pyd2bot into the .venv : 
   1. crate a file `pydofus2.pth` in the root od the folder `.venv` and write in it the absolute path to pydofus2 folder.
   2. crate a file `pyd2bot.pth` in the root od the folder `.venv` and write in it the absolute path to pyd2bot folder.
For example in my env, pydofus2.pth is situated in : d:/botdev/.venv/pydofus2.pth and contains `D:\botdev\pyd2bot`
### Install dependencies:
- Source .venv: `source .venv/Scripts/activate`
- Install dependencies for pyd2bot: `pip install -r pyd2bot/requirements.txt`
- Install dependencies for pydofus2: `pip install -r pydofus2/requirements.txt`
Note that some dependencies might be missing in the requirement files so you might have to install them later.

### Setup config files:
- In `pydofus2.pydofus2.com.ankamagames.dofus.Constants`, set:
  - `DOFUS_ROOTDIR` to your Dofus installation directory (where `invoker.swf` is located)
  - `LANG_FILE_PATH` to your Dofus lang file (e.g., `LANG_FILE_PATH = DOFUS_DATA_DIR / "i18n" / "i18n_fr.d2i"`)
- Other paths can be adjusted as needed if you know what you are doing.

### Change Makefile for regenerating Dofus protocol:
- Edit `<pydofus2_dir>\pydofus2\devops\Makefile`
- Set variables correctly (e.g., `DOFUSINVOKER`, `PYDOFUS_DIR`, `PYD2BOT_DIR`, `GRINDER_DIR`, `VENV_DIR`)
- Example setup:
```bash
DOFUSINVOKER = D://Dofus//DofusInvoker.swf
PYDOFUS_DIR = D://botdev//pydofus2
PYD2BOT_DIR = D://botdev//pyd2bot
GRINDER_DIR = D://botdev/Grinder
VENV_DIR = D://botdev//.venv
```
One way to use the devops pipeline is to update the protocol after a new dofus maj:
For that you simply launch `make update`, this will regenerate the new protocol specs, update the message shuffling and générate new set of message classes in their respective folder under the pydofus2 folders hirarchy.

### Set logs directory:
For logging you need to specify the path you want the folder of logs to be situated.
- In `<pydofus2_dir>\pydofus2\com\ankamagames\jerakine\logger\Logger.py`, set `LOGS_PATH` (e.g., `LOGS_PATH = Path("D:/botdev/logs")`)

### Generate keys and unpack maps:
- Navigate to `<pydofus2_dir>\pydofus2\devops`
- Run `make extract-keys` and `make unpack-maps`
Note that this is done in the `make update` pipeline.
### If you want to start the sniffer app:
- Navigate to `<pydofus2_dir>\pydofus2\sniffer`
- Install requirements: `pip install -r requirements.txt`
- Run the app: `python app.py`

## Import your account and character data, run a bot example
To import your account and character data into pyd2bot, follow these steps:

1. **Obtain your HAAPI API key:**
   - Use a local proxy and configure your operating system to route requests to it.
   - Log in to your account in the Ankama Launcher.
   - Find your API key in the header of the call to `https://haapi.ankama.com/json/Ankama/v5/Account/CreateToken`.
Personaly i use mitmproxy-10.2 for windows, i run it on localhost:8080, i install its certificate and i configure windows to use it. Then i open its web interface and i connect to my bot account trough the launcher and i look for the request i mentioned above.
This proces is done once in a month because the apikey has a one month expiration date.

2. **Update the script with your API key:**
   - Go to `<pyd2bot_dir>/launch_bot_test`.
   - In the `fetch_account_data.py` script, replace `api_key` with your own API key.
   - Run the script. This will create a JSON file with your account data and store it in `<pyd2bot_dir>/pyd2bot/persistence/accounts.json`.

3. **Configure and run the bot example:**
   - Open the `run_resourceFarmBot.py` script.
   - Replace `accountId` with your account ID (it should be the key of your account data in the `accounts.json` file).
   - Run the script, a log file should appear in the logs dir you configured and you can see in it detailed logs on whats happening with your bot.

By following these steps, your account and character data will be successfully imported into pyd2bot, allowing you to start using the bot with your personal data.