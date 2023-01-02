import json
import os
from pathlib import Path
from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_v1_5 
from pyd2bot.BotConstants import BotConstants
import base64

CURRDIR = Path(__file__).parent
KEYS_DIR = BotConstants.KEYS_DIR
CREDS_DB = BotConstants.PERSISTENCE_DIR / "accounts.json"
pubkey_p = KEYS_DIR / "public.pem"
privatekey_p = KEYS_DIR / "private.pem"


class AccountCredsManager:
    with open(pubkey_p, "rb") as fp:
        _pubkey = RSA.import_key(fp.read())
    with open(privatekey_p, "rb") as fp:
        _privatekey = RSA.import_key(fp.read())
    if not os.path.exists(CREDS_DB):
        with open(CREDS_DB, "w") as fp:
            json.dump({}, fp)
    with open(CREDS_DB, "r") as fp:
        _creds = json.load(fp)

    @classmethod
    def addEntry(cls, name, username, password):
        password = cls.encryptPasssword(password)
        cls._creds.update({name: {"login": username, "password": password}})
        with open(CREDS_DB, "w") as fp:
            json.dump(cls._creds, fp, indent=4)

    @classmethod
    def getEntry(cls, name):
        if name not in cls._creds:
            raise Exception(f"No registred account creds for account {name}")
        result = cls._creds.get(name).copy()
        result["password"] = cls.decryptPasssword(result["password"])
        return result

    @classmethod
    def encryptPasssword(cls, password: str) -> str:
        rsacipher = PKCS1_v1_5.new(cls._pubkey)
        baIn = base64.b64decode(password)
        encryptedPass = base64.b64encode(rsacipher.encrypt(baIn))
        return encryptedPass

    @staticmethod
    def decryptPasssword(encryptedPass: str) -> str:
        cipher = PKCS1_v1_5.new(AccountCredsManager._privatekey)
        encryptedPass = base64.b64decode(encryptedPass.encode('utf-8'))
        password_ba = cipher.decrypt(encryptedPass, None)
        password = password_ba.decode("utf-8")
        return password


if __name__ == "__main__":
    newdb = AccountCredsManager._creds
    for key, value in newdb.items():
        pwd = AccountCredsManager.decryptPasssword(newdb[key]["password"])
        import os
        from subprocess import Popen, PIPE
        launcher_dir = os.path.dirname(__file__) + "/../../launcher"
        print(CURRDIR)
        p = Popen(
            ["cd", launcher_dir, "&&", "node", "getCertificate.js", newdb[key]["login"]],
            stderr=PIPE,
            stdout=PIPE,
            shell=True,
        )
        stdout, stderr = p.communicate()
        if stderr:
            raise Exception(stderr.decode("utf-8"))
        ret_json = stdout.decode("utf-8")
        cert = json.loads(ret_json)
        print(cert)
        print("login: ", newdb[key]["login"])
        print("pwd: ", pwd)