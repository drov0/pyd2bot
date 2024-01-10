import json
import os

from pyd2bot.thriftServer.pyd2botServer import Pyd2botServer
from pyd2bot.thriftServer.pyd2botService.ttypes import Character
from pydofus2.com.ankamagames.atouin.Haapi import Haapi

__dir__ = os.path.dirname(os.path.abspath(__file__))
persistence_dir = "D://botdev//persistence"
accounts_jsonfile = os.path.join(persistence_dir, "accounts.json")

class AccountManager:
    
    with open(accounts_jsonfile, 'r') as fp:
        accounts : dict = json.load(fp)

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
    def get_apikey(cls, accountId):
        acc = cls.getAccount(accountId)
        return acc["apikey"]

    @classmethod
    def fetch_account(cls, game, apikey):
        import asyncio
        r = asyncio.run(Haapi.signOnWithApikey(game, apikey))
        accountId = r['id']
        cls.accounts[accountId] = r['account']
        cls.accounts[accountId]["apikey"] = apikey
        return cls.fetch_characters(accountId)
        
    @classmethod
    def fetch_characters(cls, accountId):
        acc = cls.getAccount(accountId)
        apikey = acc['apikey']
        token = Haapi.getLoginTokenCloudScraper(1, apikey)
        srv = Pyd2botServer("test")
        chars = srv.fetchCharacters(token)
        chars_json = [
            {
                "name": ch.name,
                "id": ch.id,
                "level": ch.level,
                "breedId": ch.breedId,
                "breedName": ch.breedName,
                "serverId": ch.serverId,
                "serverName": ch.serverName,
                "login": acc['login'],
                "accountId": accountId
            } for ch in chars
        ]
        cls.accounts[accountId]["characters"] = chars_json
        cls.save()
        return chars_json
        
    
    @classmethod
    def save(cls):
        with open(accounts_jsonfile, 'w') as fp:
            json.dump(cls.accounts, fp, indent=4)
    