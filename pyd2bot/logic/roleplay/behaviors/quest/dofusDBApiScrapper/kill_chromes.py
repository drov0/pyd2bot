import subprocess
import os

def kill_chrome():
    if os.name == 'nt':  # for Windows
        subprocess.call("taskkill /IM chrome.exe /F", shell=True)
    else:  # for Linux/OS X
        subprocess.call(["killall", "Google Chrome"])

kill_chrome()