import json
import os

from pyd2bot.thriftServer.pyd2botService.ttypes import Character

__dir = os.path.dirname(os.path.abspath(__file__))
persistence_dir = os.path.join(__dir, "..", "..", "..", "..", "Grinder", "dist_electron", "persistence")
accounts_jsonfile = os.path.join(persistence_dir, "accounts.json")
creds_jsonfile = os.path.join(persistence_dir, "credentials.json")

class AccountManager:
    
    with open(accounts_jsonfile, 'r') as fp:
        accounts : dict = json.load(fp)
    with open(creds_jsonfile, 'r') as fp:
        creds: dict = json.load(fp)
    certificates = creds["certificates"]
    apikeys = creds["apikeys"]

    @classmethod
    def getAccount(cls, accountId):
        return cls.accounts[accountId]

    @classmethod
    def getCharacter(cls, accountId, charId=None):
        characterJson = None
        if charId is None:
            characterJson = cls.accounts[accountId]["characters"][0]
        else:
            for ch in cls.accounts[accountId]["characters"].values():
                if ch["id"] == charId:
                    characterJson = ch
        if characterJson is None:
            return None
        return Character(
            name=characterJson["name"],
            id=characterJson["id"],
            level=characterJson["level"],
            breedId=characterJson["breedId"],
            breedName=characterJson["breedName"],
            serverId=characterJson["serverId"],
            serverName=characterJson["serverName"],
            login=characterJson["login"],
            accountId=characterJson["accountId"]
        )
    
    @classmethod
    def getCert(cls, accountId):
        acc = cls.getAccount(accountId)
        return cls.certificates.get(acc["login"])
    
    @classmethod
    def getkey(cls, accountId):
        acc = cls.getAccount(accountId)
        return cls.apikeys.get(acc["login"])


if __name__ == "__main__":
    print(AccountManager.getCert("173257465"))