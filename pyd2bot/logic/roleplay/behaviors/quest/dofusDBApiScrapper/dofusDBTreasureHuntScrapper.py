import asyncio
import concurrent.futures
import os
import random
from urllib.parse import parse_qs, urlparse
from .db.DofusPoiDB import DofusPoiDB

import pyppeteer
from lxml import html
from pyppeteer import launch
from pyppeteer.element_handle import ElementHandle
from pyppeteer.network_manager import Response
from pyppeteer_stealth import stealth

from pydofus2.com.ankamagames.dofus.datacenter.world.MapPosition import \
    MapPosition
from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.WorldGraph import \
    WorldGraph
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.types.enums.DirectionsEnum import \
    DirectionsEnum

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://dofusdb.fr/fr/tools/treasure-hunt"
ICON_CLASSES = {
    DirectionsEnum.UP: "fa-arrow-up",
    DirectionsEnum.DOWN: "fa-arrow-down",
    DirectionsEnum.LEFT: "fa-arrow-left",
    DirectionsEnum.RIGHT: "fa-arrow-right",
}
DIRECTION_COORD = {
    DirectionsEnum.UP: (0, -1),
    DirectionsEnum.DOWN: (0, 1),
    DirectionsEnum.RIGHT: (1, 0),
    DirectionsEnum.LEFT: (-1, 0),
}
MP_BY_COORD = dict[tuple[int, int], MapPosition]()
MP_BY_ID = dict[int, MapPosition]()
for mp in MapPosition.getMapPositions():
    if mp.worldMap == 1:
        MP_BY_COORD[(mp.posX, mp.posY)] = mp
        MP_BY_ID[mp.id] = mp
REQ_TIMEOUT = 5.0  # time to wait for a response in seconds
REQ_RETRY = 20  # number of retries if a request times out
USER_DATA_DIR = os.path.join(os.getenv('LOCALAPPDATA'), "Google", "Chrome", "User Data")

def run_scraper_in_new_event_loop(worker_id: int):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    scraper = DofusDBScraper(worker_id)
    loop.run_until_complete(scraper.run())
    scraper.db.ex()
    loop.close()

class DofusDBScraper:
    WINDOW_WIDTH = 600
    WINDOW_HIGHT = 1000

    def __init__(self, worker_id):
        self.browser = None
        self.stop_flag = False
        self.db: DofusPoiDB = None
        self.worldGraph = None
        self.futures = {}
        self.token_future = None
        self.page = None
        self.worker_id = worker_id

    async def newBrowser(self):
        return await launch(
            headless=False,
            executablePath=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            defaultViewport=None,
            args=["--new-window", "--no-sandbox", "--disable-setuid-sandbox", "--incognito"]
        )
        
    async def initialize(self):
        self.db = DofusPoiDB()
        self.worldGraph = WorldGraph()
        Logger().debug(f"[Worker-{self.worker_id}] Creating browser ...")
        self.browser = await self.newBrowser()
        Logger().debug(f"[Worker-{self.worker_id}] browser created")
        await asyncio.sleep(2)
        self.page = await self.browser.newPage()
        await stealth(self.page)
        Logger().debug(f"[Worker-{self.worker_id}] browser new page created")
        Logger().debug(f"[Worker-{self.worker_id}] Loading page")
        self.page.on(
            "response", lambda resp: asyncio.ensure_future(self.interceptResponse(resp))
        )
        self.token_future = asyncio.Future()
        await self.page.goto(BASE_URL, waitUntil='domcontentloaded')
        Logger().debug(f"[Worker-{self.worker_id}] Treasure hunt page loaded")
        await asyncio.sleep(3)
        Logger().debug(f"[Worker-{self.worker_id}] - Initialized")
        await self.main()

    async def interceptResponse(self, response: Response):
        if response.request.method == "GET":
            if "https://api.dofusdb.fr/treasure-hunt" in response.request.url:
                await self.processPoiDataResp(response)
            elif "https://www.google.com/recaptcha/enterprise/anchor" in response.request.url:
                await self.processCaptchaResp(response)
    
    async def processCaptchaResp(self, response: Response):
        try:
            resp_text = await response.text()
            if "recaptcha-token" in resp_text:
                self.token_future.set_result(True)
                Logger().warning("Received token!")
            root = html.fromstring(resp_text)
            token_elements = root.xpath('//input[@id="recaptcha-token"]/@value')
            if token_elements:
                self.token_future.set_result(token_elements[0])
                Logger().warning("[Worker-{self.worker_id}] Received token!")
        except Exception as e:
            Logger().error(f"[Worker-{self.worker_id}] Unable to process captcha resp")
        
    def getParamsFroMResp(self, response: Response):
        parsed_url = urlparse(response.request.url)
        qs = parse_qs(parsed_url.query)
        return (int(qs["x"][0]), int(qs["y"][0]), int(qs["direction"][0]))
    
    async def processPoiDataResp(self, response: Response):
        params = self.getParamsFroMResp(response)
        Logger().debug(f"[Worker-{self.worker_id}] <=== Received dofusDB data for: {params}")
        Logger().debug(f"[Worker-{self.worker_id}] STATUS: {response.status}")
        json_response = await response.json()
        if response.status == 503:
            Logger().error(f"[Worker-{self.worker_id}] Request to server failed: {json_response}")
            return
        data = json_response.get("data", [])
        if not data:
            Logger().warning(f"[Worker-{self.worker_id}] Received response without data : {json_response}")
        else:
            for mapInfo in data:
                map_id = mapInfo["id"]
                pois_to_add = []
                for poi in mapInfo["pois"]:
                    if not self.db.is_poi_present(map_id, poi["id"]):
                        pois_to_add.append(poi["id"])
                    else:
                        Logger().debug(f"[Worker-{self.worker_id}] Poi {poi['id']} already scrapped for map {map_id}")
                if pois_to_add:
                    self.db.add_pois_to_map(map_id, pois_to_add)
        self.db.add_processed_request(**self.curr_request)
        self.futures[params].set_result(json_response)

    async def stop(self):
        await self.browser.close()

    def needScrapDirection(self, mapId, direction):
        currMp = MP_BY_ID[mapId]
        dx, dy = DIRECTION_COORD[direction]
        nextCoords = [(currMp.posX, currMp.posY)] + [(currMp.posX + dx, currMp.posY + dy) for _ in range(10)]
        for coord in nextCoords:
            if coord not in MP_BY_COORD:
                continue
            currMp = MP_BY_COORD[coord]
            if not self.canChangeMap(currMp.id, direction):
                Logger().debug(
                    f"[Worker-{self.worker_id}] !!! can't change map from {currMp.id} to the {direction}"
                )
                return False
            if not self.db.is_map_exists(currMp.id):
                return True
        Logger().debug(f"[Worker-{self.worker_id}] !!! All maps in direction scrapped already")
        return False

    def canChangeMap(self, mapId, direction):
        if not self.worldGraph.getVertices(mapId):
            return False
        for vertex in self.worldGraph.getVertices(mapId).values():
            for edge in self.worldGraph.getOutgoingEdgesFromVertex(vertex):
                for transition in edge.transitions:
                    if (
                        transition.direction
                        and DirectionsEnum(transition.direction) == direction
                    ):
                        return True
        return False

    async def scrap(self, mp: MapPosition):
        coordsSet = False
        for direction in DIRECTION_COORD:
            self.curr_request = {
                "map_id": mp.id,
                "x": mp.posX,
                "y": mp.posY,
                "direction": direction.value,
            }
            params = (int(mp.posX), int(mp.posY), int(direction.value))
            if self.db.is_query_processed(*params):
                Logger().warning(f"[Worker-{self.worker_id}] Query {params} previously processed")
                continue

            if self.needScrapDirection(mp.id, direction):
                if not coordsSet:
                    await self.setCoordinates(mp.posX, mp.posY)
                    coordsSet = True
                self.futures[params] = asyncio.Future()
                await self.clickArrow(direction)
                for _ in range(REQ_RETRY):
                    try:
                        Logger().debug(f"[Worker-{self.worker_id}] Request {params} sent waiting for server response ...")
                        await asyncio.wait_for(
                            self.futures[params], timeout=REQ_TIMEOUT
                        )
                        Logger().debug(f"vRequest {params} response received!")
                        del self.futures[params]
                        await asyncio.sleep(1)
                        break
                    except asyncio.exceptions.TimeoutError:
                        Logger().debug(
                            f"[Worker-{self.worker_id}] Server did not respond within {REQ_TIMEOUT} seconds for map {mp.id} and direction {direction}. Reloading page and retrying."
                        )
                        await self.page.reload(waitUntil="domcontentloaded")
                        self.futures[params] = asyncio.Future()
                        await self.setCoordinates(mp.posX, mp.posY)
                        await self.clickArrow(direction)
                else:
                    Logger().debug(
                        f"[Worker-{self.worker_id}] Server did not respond after {REQ_RETRY} attempts for map {mp.id} and direction {direction}. Skipping."
                    )
            else:
                Logger().debug(f"[Worker-{self.worker_id}] <== Skipping {params}")
                self.db.add_processed_request(**self.curr_request)

    async def setCoordinates(self, x, y):
        input_x: ElementHandle = await self.page.waitForXPath(
            "//input[@placeholder='X']", options={"visible": True}
        )
        await input_x.click()
        await self.page.keyboard.down("Control")
        await self.page.keyboard.press("A")
        await self.page.keyboard.up("Control")
        await input_x.type(str(x))
        input_y: ElementHandle = await self.page.waitForXPath(
            "//input[@placeholder='Y']", options={"visible": True}
        )
        await input_y.click()
        await self.page.keyboard.down("Control")
        await self.page.keyboard.press("A")
        await self.page.keyboard.up("Control")
        await input_y.type(str(y))

    async def clickArrow(self, direction: DirectionsEnum):
        MAX_RETRIES = 10
        arrow_icon_class = ICON_CLASSES[direction]
        for i in range(MAX_RETRIES):
            try:
                arrow_element: ElementHandle = await self.page.waitForXPath(
                    f"//i[contains(@class, '{arrow_icon_class}')]",
                    options={"visible": True},
                )
                await arrow_element.click()
            except pyppeteer.errors.ElementHandleError as e:
                Logger().error(
                    f"[Worker-{self.worker_id}] Error occurred while clicking on the element with class {arrow_icon_class}: {str(e)}"
                )
                if i < MAX_RETRIES - 1:
                    await self.page.reload(waitUntil="domcontentloaded")
                    await self.setCoordinates(self.page, 
                        self.curr_request["x"], self.curr_request["y"]
                    )

    async def main(self):
        try:
            mps = list(mp for mp in MP_BY_ID.values() if not self.db.is_map_processed(mp.posX, mp.posY))
            random.shuffle(mps)
            for mp in mps:
                await self.scrap(mp)
                await asyncio.sleep(1)  # Sleep for a while before moving to the next chunk
        except KeyboardInterrupt:
            Logger().debug(f"[Worker-{self.worker_id}] Scraper interrupted by keyboard interrupt")
        finally:
            await self.stop()

    async def run(self):
        await self.initialize()
        await self.stop()
        Logger().debug("Done !")

if __name__ == "__main__":
    import sys

    worker_id = int(sys.argv[1])
    run_scraper_in_new_event_loop(worker_id)
    