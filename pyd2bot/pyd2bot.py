import queue
import threading
import time
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pyd2bot.thriftServer.pyd2botServer import Pyd2botServer
from thrift.protocol.THeaderProtocol import THeaderProtocolFactory
import pyd2bot.thriftServer.pyd2botService.Pyd2botService as Pyd2botService
from pydofus2.com.ankamagames.jerakine.metaclasses.Singleton import Singleton
from thrift.transport import TTransport
from thrift.transport.TSocket import TSocket, TServerSocket
from thrift.protocol import TBinaryProtocol

class PyD2Bot(metaclass=Singleton):
    _stop = threading.Event()
    id: str
    logger = None
    _running_threads = list[threading.Thread]()
    _daemon: int
    processor = None
    serverTransport = None
    inputTransportFactory = None
    inputProtocolFactory = None
    
    def __init__(self, id:str, host: str, port: int, deamon=False) -> None:
        self.id = id
        self.host = host
        self.port = port
        self._daemon = deamon
        Logger.prefix = id
        self.logger = Logger()
        self.handler = Pyd2botServer(self.id)       
        self.processor = Pyd2botService.Processor(self.handler)
        self.inputTransportFactory = self.outputTransportFactory = TTransport.TBufferedTransportFactory()
        self.inputProtocolFactory = self.outputProtocolFactory = TBinaryProtocol.TBinaryProtocolFactory()
    
    def runServer(self):
        self._stop.clear()
        self.serverTransport = TServerSocket(host=self.host, port=self.port)
        self.logger.info(f"[Server - {self.id}] Threads started")
        # Pump the socket for clients
        self.serverTransport.listen()
        self.logger.info(f"[Server - {self.id}] Started listening on {self.host}:{self.port}")
        while not self._stop.is_set():
            try:
                client: TSocket = self.serverTransport.accept()
                if not client:
                    continue
                t = threading.Thread(target=self.serveClient, args=(client,))
                t.setDaemon(self._daemon)
                t.start()
                self._running_threads.append(t)
                self.logger.info(f"[Server - {self.id}] Accepted client: {client}")
            except Exception as x:
                self.logger.exception(x)
        self.logger.info(f"[Server - {self.id}] Goodbye crual world!")

    def runClient(self, host: str, port: int):
        transport = TSocket(host, port)
        transport = TTransport.TBufferedTransport(transport)
        protocol = TBinaryProtocol.TBinaryProtocol(transport)
        client = Pyd2botService.Client(protocol)
        for k in range(5):
            try:
                transport.open()
                return transport, client
            except Exception as x:
                self.logger.exception(x)
                time.sleep(5)
                continue
        raise Exception("Can't connect to server")
        
    def serveClient(self, client: TSocket):
        """Process input/output from a client for as long as possible"""
        itrans = self.inputTransportFactory.getTransport(client)
        iprot = self.inputProtocolFactory.getProtocol(itrans)

        # for THeaderProtocol, we must use the same protocol instance for input
        # and output so that the response is in the same dialect that the
        # server detected the request was in.
        if isinstance(self.inputProtocolFactory, THeaderProtocolFactory):
            otrans = None
            oprot = iprot
        else:
            otrans = self.outputTransportFactory.getTransport(client)
            oprot = self.outputProtocolFactory.getProtocol(otrans)

        try:
            while not self._stop.is_set():
                self.processor.process(iprot, oprot)
        except TTransport.TTransportException:
            pass
        except Exception as x:
            self.logger.exception(x)

        itrans.close()
        if otrans:
            otrans.close()
        client.close()
            
    def stopServer(self):
        self.logger.info(f"[Server - {self.id}] Stop called")
        self._stop.set()