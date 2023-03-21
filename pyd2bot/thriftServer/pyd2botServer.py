import functools
import json
import sys
import threading
import traceback
from time import sleep

from pyd2bot.logic.common.frames.BotCharacterUpdatesFrame import \
    BotCharacterUpdatesFrame
from pyd2bot.logic.common.frames.BotWorkflowFrame import BotWorkflowFrame
from pyd2bot.logic.managers.BotConfig import BotConfig
from pyd2bot.logic.roleplay.behaviors.CreateNewCharacter import \
    CreateNewCharacter
from pyd2bot.logic.roleplay.behaviors.GetOutOfAnkarnam import GetOutOfAnkarnam
from pyd2bot.thriftServer.pyd2botService.ttypes import (Character, DofusError,
                                                        Server, Session,
                                                        SessionType, Spell)
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import (
    KernelEvent, KernelEventsManager)
from pydofus2.com.ankamagames.dofus.kernel.Kernel import Kernel
from pydofus2.com.ankamagames.dofus.logic.common.actions.ChangeServerAction import \
    ChangeServerAction
from pydofus2.com.ankamagames.dofus.logic.connection.actions.ServerSelectionAction import \
    ServerSelectionAction
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.InventoryManager import \
    InventoryManager
from pydofus2.com.ankamagames.dofus.logic.game.common.managers.PlayedCharacterManager import \
    PlayedCharacterManager
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.DofusClient import DofusClient


def getTrace(e):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback_in_var = traceback.format_tb(exc_traceback)
    error_trace = "\n".join([str(e), str(exc_type), str(exc_value), "\n".join(traceback_in_var)])
    return error_trace


lock = threading.Lock()


def sendTrace(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise DofusError(0, getTrace(e))

    return wrapped


class Pyd2botServer:
    def __init__(self, id: str):
        self.id = id

    @sendTrace
    def fetchUsedServers(self, token: str) -> list[Server]:
        from pydofus2.com.ankamagames.dofus.network.types.connection.GameServerInformations import \
            GameServerInformations

        Logger().debug("fetchUsedServers called with token: " + token)
        client = DofusClient("fetchServersThread")
        client._loginToken = token
        client._serverId = 0
        result = None
        client.start()
        KernelEventsManager.WaitThreadRegister("fetchServersThread", 25)
        servers: dict[str, list[GameServerInformations]] = KernelEventsManager.getInstance("fetchServersThread").wait(
            KernelEvent.SERVERS_LIST, 60
        )
        Logger().info(f"List servers: {[s.to_json() for s in servers['used']]}")
        result = [
            Server(
                server.id,
                server.status,
                server.completion,
                server.charactersCount,
                server.charactersSlots,
                server.date,
                server.isMonoAccount,
                server.isSelectable,
            )
            for server in servers["used"]
        ]
        client.shutdown()
        return result

    @sendTrace
    def fetchCharacters(self, token: str) -> list[Character]:
        from pydofus2.com.ankamagames.dofus.internalDatacenter.connection.BasicCharacterWrapper import \
            BasicCharacterWrapper
        from pydofus2.com.ankamagames.dofus.logic.common.managers.PlayerManager import \
            PlayerManager
        from pydofus2.com.ankamagames.dofus.network.types.connection.GameServerInformations import \
            GameServerInformations

        instanceName = "fetchCharactersThread"
        result = list()
        client = DofusClient(instanceName)
        client._loginToken = token
        client._serverId = 0
        client.start()
        KernelEventsManager.WaitThreadRegister(instanceName, 25)
        servers: dict[str, list[GameServerInformations]] = KernelEventsManager.getInstance(instanceName).wait(
            KernelEvent.SERVERS_LIST, 60
        )
        first = True
        for server in servers["used"]:
            if first:
                first = False
                Kernel.getInstance(instanceName).worker.process(ServerSelectionAction.create(server.id))
            else:
                Kernel.getInstance(instanceName).worker.process(ChangeServerAction.create(server.id))
            charactersList: list[BasicCharacterWrapper] = KernelEventsManager.getInstance(instanceName).wait(
                KernelEvent.CHARACTERS_LIST, 60
            )
            result += [
                Character(
                    character.name,
                    character.id,
                    character.level,
                    character.breedId,
                    character.breed.name,
                    PlayerManager.getInstance(instanceName).server.id,
                    PlayerManager.getInstance(instanceName).server.name,
                )
                for character in charactersList
            ]
        client.shutdown()
        return result

    @sendTrace
    def runSession(self, token: str, session: Session) -> None:
        if session.type == SessionType.FIGHT:
            BotConfig().initFromSession(session, "leader")
            DofusClient().registerInitFrame(BotWorkflowFrame)
            DofusClient().registerGameStartFrame(BotCharacterUpdatesFrame)
            serverId = session.leader.serverId
            characId = session.leader.id
            DofusClient().login(token, serverId, characId)
            for character in session.followers:
                BotConfig().initFromSession(session, "follower", character)
        else:
            raise Exception(f"Unsupported session type: {session.type}")

    def fetchBreedSpells(self, breedId: int) -> list["Spell"]:
        from pydofus2.com.ankamagames.dofus.datacenter.breeds.Breed import \
            Breed

        spells = []
        breed = Breed.getBreedById(breedId)
        if not breed:
            raise Exception(f"Breed {breedId} not found.")
        for spellVariant in breed.breedSpellVariants:
            for spellBreed in spellVariant.spells:
                spells.append(Spell(spellBreed.id, spellBreed.name))
        return spells

    def fetchJobsInfosJson(self) -> str:
        from pydofus2.com.ankamagames.dofus.datacenter.jobs.Skill import Skill

        res = {}
        skills = Skill.getSkills()
        for skill in skills:
            if skill.gatheredRessource:
                if skill.parentJobId not in res:
                    res[skill.parentJobId] = {
                        "id": skill.parentJobId,
                        "name": skill.parentJob.name,
                        "gatheredRessources": [],
                    }
                gr = {
                    "name": skill.gatheredRessource.name,
                    "id": skill.gatheredRessource.id,
                    "levelMin": skill.levelMin,
                }
                if gr not in res[skill.parentJobId]["gatheredRessources"]:
                    res[skill.parentJobId]["gatheredRessources"].append(gr)
        return json.dumps(res)

    def moveToVertex(self, vertex: str):
        from pyd2bot.logic.roleplay.messages.MoveToVertexMessage import \
            LeaderPosMessage
        from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Vertex import \
            Vertex

        v = Vertex(**json.loads(vertex))
        Logger().debug(f"Leader pos given, leader in vertex {v}.")
        Kernel().worker.process(LeaderPosMessage(v))

    def followTransition(self, transition: str):
        from pyd2bot.logic.roleplay.messages.FollowTransitionMessage import \
            FollowTransitionMessage
        from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Transition import \
            Transition

        tr = Transition(**json.loads(transition))
        Kernel().worker.process(FollowTransitionMessage(tr))
        print("LeaderTransitionMessage processed")

    def getStatus(self) -> str:
        from pyd2bot.apis.PlayerAPI import PlayerAPI

        status = PlayerAPI().status
        print(f"get staus called -> Status: {status}")
        return status

    def comeToBankToCollectResources(self, bankInfos: str, guestInfos: str):
        from pyd2bot.logic.roleplay.behaviors.CollectItems import CollectItems
        from pyd2bot.misc.Localizer import BankInfos

        with lock:
            bankInfos = BankInfos(**json.loads(bankInfos))
            guestInfos = json.loads(guestInfos)
            CollectItems(
                bankInfos,
                guestInfos,
                None,
                lambda r, err: Logger().info(f"CollectItems finished: {r} {err}"),
            )

    def getCurrentVertex(self) -> str:
        return json.dumps(PlayedCharacterManager().currVertex.to_json())

    def getInventoryKamas(self) -> int:
        kamas = int(InventoryManager().inventory.kamas)
        return int(kamas)

    def startUp(self, token):
        client = DofusClient("startup")
        client._loginToken = token
        client._serverId = 294
        client.start()
        KernelEventsManager.WaitThreadRegister("startup", 25)
        Logger().info("kernel event manager instance created")

        def onGetOutOfIncarnamEnded(status, error):
            if error:
                Logger().info(error)
            else:
                Logger().info("Character now is in astrub")
            client.shutdown()

        def onNewCharacterEnded(status, error):
            if error:
                Logger().info(error)
                return client.shutdown()
            else:
                Logger().info("character created successfully")
            GetOutOfAnkarnam().start(callback=onGetOutOfIncarnamEnded)

        def onCharactersList(event, return_value):
            Logger().info("characters list received")
            sleep(3)
            CreateNewCharacter().start(10, callback=onNewCharacterEnded)

        KernelEventsManager.getInstance("startup").once(KernelEvent.CHARACTERS_LIST, onCharactersList)
        Logger().info("ended in peace")
