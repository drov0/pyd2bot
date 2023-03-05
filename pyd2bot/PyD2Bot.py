import threading
import time
from pyd2bot.thriftServer.pyd2botServer import Pyd2botServer
from thrift.protocol.THeaderProtocol import THeaderProtocolFactory
from thrift.protocol.TJSONProtocol import TJSONProtocolFactory
import pyd2bot.thriftServer.pyd2botService.Pyd2botService as Pyd2botService
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.metaclasses.Singleton import Singleton
from thrift.transport import TTransport
from thrift.transport.TSocket import TSocket, TServerSocket
from thrift.protocol import TBinaryProtocol
from thrift.server import THttpServer
from pyd2bot.thriftServer.HttpRequestHandler import getReqHandler


class PyD2Bot(metaclass=Singleton):
    _stop = threading.Event()
    id: str
    _running_threads = list[threading.Thread]()
    _daemon: int
    processor = None
    serverTransport = None
    inputTransportFactory = None
    inputProtocolFactory = None

    def __init__(self, id: str, host: str, port: int, deamon=False) -> None:
        self.id = id
        self.host = host
        self.port = port
        self._daemon = deamon
        self.handler = Pyd2botServer(self.id)
        self.processor = Pyd2botService.Processor(self.handler)

    def runHttpServer(self):
        self.serverTransport = THttpServer.THttpServer(self.processor, (self.host, self.port), TJSONProtocolFactory())
        self.serverTransport.httpd.RequestHandlerClass = getReqHandler(self.serverTransport)
        Logger().info(f"[Server - {self.id}] Started serving on {self.host}:{self.port}")
        self.serverTransport.serve()

    def stopServer(self):
        Logger().info(f"[Server - {self.id}] Stop called")
        self._stop.set()
