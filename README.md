# Pyd2bot: A Python Bot for Dofus

Pyd2bot utilizes the Pydofus2 client as a background to automate tasks in Dofus. This guide is tailored for beginners, especially for Windows users.

## Prerequisites:
- **Python 3.9.11**: Download and install from [python.org](https://www.python.org/downloads/release/python-3911/).
- **Pcap and Wireshark**: Required for sniffer functionality. Download Wireshark from [here](https://www.wireshark.org/download.html).

## Setup Steps for Developers:

### 1. Setting Up the Environment
- **Create a New Folder**: 
  - Open Command Prompt.
  - Create a new folder named `botdev` and navigate into it:
    ```bash
    mkdir botdev
    cd botdev
    ```
- **Clone Repositories**:
  - Clone the `pydofus2` repository:
    ```bash
    git clone https://github.com/kmajdoub/pydofus2.git
    ```
  - Clone the `pyd2bot` repository:
    ```bash
    git clone https://github.com/kmajdoub/pyd2bot.git
    ```
- **Create a Virtual Environment**:
  - Within the `botdev` folder, execute:
    ```bash
    python -m venv .venv
    ```
- **Set Up Path Files**:
  - Create `pydofus2.pth` and `pyd2bot.pth` inside `.venv`.
  - Write the absolute path to `pydofus2` and `pyd2bot` in their respective files.
    - Example for `pydofus2.pth`: `D:\botdev\pydofus2`

### 2. Installing Dependencies
- **Activate Virtual Environment**:
  - Execute:
    ```bash
    .venv\Scripts\activate
    ```
- **Install Dependencies**:
  - For `pyd2bot`:
    ```bash
    pip install -r pyd2bot/requirements.txt
    ```
  - For `pydofus2`:
    ```bash
    pip install -r pydofus2/requirements.txt
    ```

### 3. Configuration
- **Setup Config Files**:
  - In `pydofus2.pydofus2.com.ankamagames.dofus.Constants`, configure:
    - `DOFUS_ROOTDIR`: Path to your Dofus installation directory.
    - `LANG_FILE_PATH`: Path to your Dofus language file.
- **Edit Makefile for Dofus Protocol**:
  - Modify the Makefile in `<pydofus2_dir>\pydofus2\devops\Makefile`.
  - Set variables like `DOFUSINVOKER`, `PYDOFUS_DIR`, etc.
    - Example:
      ```bash
      DOFUSINVOKER = D://Dofus//DofusInvoker.swf
      PYDOFUS_DIR = D://botdev//pydofus2
      PYD2BOT_DIR = D://botdev//pyd2bot
      VENV_DIR = D://botdev//.venv
      ```
- **Set Logs Directory**:
  - Specify the log folder path in `<pydofus2_dir>\pydofus2\com\ankamagames\jerakine\logger\Logger.py`.
    - Example: `LOGS_PATH = Path("D:/botdev/logs")`

### 4. Generate Keys and Unpack Maps
- Navigate to `<pydofus2_dir>\pydofus2\devops`.
- Execute:
```bash
make extract-keys
make unpack-maps
```
### 5. If you want to use the Sniffer App (Optional)
- Go to `<pydofus2_dir>\pydofus2\sniffer`.
- Install requirements and run the app:
```bash
pip install -r requirements.txt
python app.py
```


## Importing Account and Character Data

1. **Obtain Your HAAPI API Key**:
 - Use a local proxy like mitmproxy and configure your Windows to route requests through it.
 - Log in to your Ankama account via the Launcher.
 - Find the API key in the request header to `https://haapi.ankama.com/json/Ankama/v5/Account/CreateToken`.

2. **Update the Script with Your API Key**:
 - Navigate to `<pyd2bot_dir>/launch_bot_test`.
 - In `fetch_account_data.py`, replace `api_key` with your API key.
 - Running the script will store your account data in `accounts.json`.

3. **Configure and Run the Bot Example**:
 - Edit `run_resourceFarmBot.py`.
 - Replace `accountId` with your account ID.
 - Start the script to see the bot in action.

Follow these steps to successfully set up and run Pyd2bot on your Windows system.
