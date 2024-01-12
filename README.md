# pyd2bot
A bot that uses pydofus2 as a background client

## Prerequisites:
- Install of python 3.9.11 (other versions might work, not guaranteed)
- Install pcap and shark for sniffer functionality

## Steps for developers:
1. Create a new folder, e.g., 'botdev'
2. Clone pydofus2: `git clone https://github.com/kmajdoub/pydofus2.git`
3. Clone pyd2bot: `git clone https://github.com/kmajdoub/pyd2bot.git`

### Install dependencies:
- Source .venv: `source .venv/Scripts/activate`
- Create a new venv in the '.venv' folder
- Install dependencies: `pip install -r pyd2bot/requirements.txt` (and others as needed)

### Setup config files:
- In `pydofus2.pydofus2.com.ankamagames.dofus.Constants`, set:
  - `DOFUS_ROOTDIR` to your Dofus installation directory (where `invoker.swf` is located)
  - `LANG_FILE_PATH` to your Dofus lang file (e.g., `LANG_FILE_PATH = DOFUS_DATA_DIR / "i18n" / "i18n_en.d2i"`)
- Other paths can be adjusted as needed.

### Change Makefile for regenerating Dofus protocol:
- Edit `<pydofus2_dir>\pydofus2\devops\Makefile`
- Set variables correctly (e.g., `DOFUSINVOKER`, `PYDOFUS_DIR`, `PYD2BOT_DIR`, `GRINDER_DIR`, `VENV_DIR`)
- Example setup:
DOFUSINVOKER = D://Dofus//DofusInvoker.swf
PYDOFUS_DIR = D://botdev//pydofus2
PYD2BOT_DIR = D://botdev//pyd2bot
GRINDER_DIR = D://botdev/Grinder
VENV_DIR = D://botdev//.venv

### Set logs directory:
- In `<pydofus2_dir>\pydofus2\com\ankamagames\jerakine\logger\Logger.py`, set `LOGS_PATH` (e.g., `LOGS_PATH = Path("D:/botdev/logs")`)

### Generate keys and unpack maps:
- Navigate to `<pydofus2_dir>\pydofus2\devops`
- Run `make extract-keys` and `make unpack-maps`

### If you want to start the sniffer app:
- Navigate to `<pydofus2_dir>\pydofus2\sniffer`
- Install requirements: `pip install -r requirements.txt`
- Run the app: `python app.py`

You should now be all set up to use pyd2bot.

## Import your account and character data, run a bot example
To import your account and character data into pyd2bot, follow these steps:

1. **Obtain your HAAPI API key:**
   - Use a local proxy and configure your operating system to route requests to it.
   - Log in to your account in the Ankama Launcher.
   - Find your API key in the header of the call to `https://haapi.ankama.com/json/Ankama/v5/Account/CreateToken`.

2. **Update the script with your API key:**
   - Go to `<pyd2bot_dir>/pyd2bot/launch_bot_test`.
   - In the `fetch_account_data.py` script, replace `api_key` with your own API key.
   - Run the script. This will create a JSON file with your account data and store it in `<pyd2bot_dir>/pyd2bot/persistence/accounts.json`.

3. **Configure and run the bot example:**
   - Open the `run_resourceFarmBot.py` script.
   - Replace `accountId` with your account ID (it should be the key of your account data in the `accounts.json` file).

By following these steps, your account and character data will be successfully imported into pyd2bot, allowing you to start using the bot with your personal data.