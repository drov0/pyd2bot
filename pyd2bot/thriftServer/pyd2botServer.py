import json
import logging
import threading
from time import perf_counter, sleep
from pyd2bot.apis.PlayerAPI import PlayerAPI

from pyd2bot.logic.common.frames.BotCharacterUpdatesFrame import \
    BotCharacterUpdatesFrame
from pyd2bot.logic.common.frames.BotWorkflowFrame import BotWorkflowFrame
from pyd2bot.logic.managers.SessionManager import SessionManager, InactivityMonitor
from pyd2bot.logic.roleplay.frames.BotSellerCollectFrame import \
    BotSellerCollectFrame
from pyd2bot.logic.roleplay.messages.LeaderPosMessage import LeaderPosMessage
from pyd2bot.logic.roleplay.messages.LeaderTransitionMessage import \
    LeaderTransitionMessage
from pyd2bot.misc.Localizer import BankInfos
from pyd2bot.thriftServer.pyd2botService.ttypes import Character, Spell
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import KernelEventsManager
from pydofus2.com.ankamagames.dofus.datacenter.breeds.Breed import Breed
from pydofus2.com.ankamagames.dofus.datacenter.jobs.Skill import Skill
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.common.managers.PlayerManager import \
    PlayerManager
from pydofus2.com.ankamagames.dofus.logic.connection.frames.ServerSelectionFrame import \
    ServerSelectionFrame
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.InventoryManager import InventoryManager
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Transition import \
    Transition
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Vertex import \
    Vertex
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.WorldPathFinder import WorldPathFinder
from pydofus2.com.ankamagames.dofus.network.enums.ServerStatusEnum import \
    ServerStatusEnum
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.DofusClient import DofusClient
lock = threading.Lock()
class Pyd2botServer:
    def __init__(self, id: str):
        self.id = id
        self.logger = Logger()
    
    def fetchServersList(self, token:str) -> list[dict]:
        dofus2 = DofusClient()
        dofus2.login(token)
        gotres = threading.Event()
        result = list()
        def onServersList(event):
            KernelEventsManager().remove_listener(KernelEventsManager.SERVERS_LIST, onServersList)
            ssf : 'ServerSelectionFrame' = Kernel().getWorker().getFrame('ServerSelectionFrame')        
            result = [server.to_json() for server in ssf.usedServers]
            gotres.set()
        KernelEventsManager().add_listener(KernelEventsManager.SERVERS_LIST, onServersList)
        gotres.wait(20)
        dofus2.shutdown()
        return result
    
    def fetchCharacters(self, token:str, serverId: int) -> list[Character]:
        result = list()
        dofus2 = DofusClient()
        dofus2.login(token, serverId)
        gotres = threading.Event()
        def onCharactersList(event):
            KernelEventsManager().remove_listener(KernelEventsManager.CHARACTERS_LIST, onCharactersList)
            for character in PlayerManager().charactersList:
                chkwrgs = {
                    "name": character.name, 
                    "id": character.id, 
                    "level": character.level, 
                    "breedId": character.breedId, 
                    "breedName": character.breed.name, 
                    "serverId": serverId, 
                    "serverName": PlayerManager().server.name
                }
                result.append(Character(**chkwrgs))
            gotres.set()
        KernelEventsManager().add_listener(KernelEventsManager.CHARACTERS_LIST, onCharactersList)
        gotres.wait(20)
        dofus2.shutdown()
        return result
        
    def runSession(self, login:str, password:str, certId:str, certHash:str, apiKey: str, sessionJson:str) -> None:
        self.logger.debug(f"runSession called with login {login}")
        self.logger.debug("session: " + sessionJson)
        SessionManager().load(sessionJson)
        self.logger.debug("Session loaded")
        dofus2 = DofusClient()
        if SessionManager().type == "fight":
            dofus2.registerInitFrame(BotWorkflowFrame)
            dofus2.registerGameStartFrame(BotCharacterUpdatesFrame)
        elif SessionManager().type == "selling":
            pass
        else:
            raise Exception("Unsupported session type: %s" % SessionManager().type)
        self.logger.debug("Frames registered")
        Haapi().APIKEY = apiKey
        loginToken = Haapi().getLoginToken(login, password, certId, certHash)
        if loginToken is None:
            raise Exception("Unable to generate login token.")
        self.logger.debug(f"Generated LoginToken : {loginToken}")
        dofus2.login(loginToken, SessionManager().character["serverId"], SessionManager().character["id"])
        iam = InactivityMonitor()
        iam.start()
        
    def fetchBreedSpells(self, breedId:int) -> list['Spell']:
        spells = []
        breed = Breed.getBreedById(breedId)
        if not breed:
            raise Exception(f"Breed {breedId} not found.")
        for spellVariant in breed.breedSpellVariants:
            for spellBreed in spellVariant.spells:
                spells.append(Spell(spellBreed.id, spellBreed.name))
        return spells
    
    def fetchJobsInfosJson(self) -> str:
        res = {}
        skills = Skill.getSkills()
        for skill in skills:
            if skill.gatheredRessource:
                if skill.parentJobId not in res:
                    res[skill.parentJobId] = { 
                        "id" : skill.parentJobId,
                        "name": skill.parentJob.name,
                        "gatheredRessources": [] 
                    }
                gr = {
                    "name": skill.gatheredRessource.name, 
                    "id": skill.gatheredRessource.id, 
                    "levelMin": skill.levelMin
                }
                if gr not in res[skill.parentJobId]["gatheredRessources"]:
                    res[skill.parentJobId]["gatheredRessources"].append(gr)
        return json.dumps(res)
    
    def getApiKey(self, login:str, password:str, certId:str, certHash:str) -> str:
        response = Haapi().createAPIKEY(login, password, certId, certHash, game_id=102)
        return json.dumps(response)

    def moveToVertex(self, vertex: str):
        v = Vertex(**json.loads(vertex))
        self.logger.debug(f"Leader pos given, leader in vertex {v}.")
        Kernel().getWorker().process(LeaderPosMessage(v))
        
    def followTransition(self, transition: str):        
        tr = Transition(**json.loads(transition))
        Kernel().getWorker().process(LeaderTransitionMessage(tr))
        print("LeaderTransitionMessage processed")
        
    def getStatus(self) -> str:
        status = PlayerAPI.status()
        print(f"get staus called -> Status: {status}")
        return status

    def comeToBankToCollectResources(self, bankInfos: str, guestInfos: str):
        with lock:
            bankInfos = BankInfos(**json.loads(bankInfos))
            guestInfos = json.loads(guestInfos)
            Kernel().getWorker().addFrame(BotSellerCollectFrame(bankInfos, guestInfos))
    
    def getCurrentVertex(self) -> str:
        return json.dumps(WorldPathFinder().currPlayerVertex.to_json())
    
    def getInventoryKamas(self) -> int:
        kamas = int(InventoryManager().inventory.kamas)
        return int(kamas)
