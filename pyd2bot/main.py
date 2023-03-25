from thrift.protocol.TJSONProtocol import TJSONProtocolFactory
from thrift.server import THttpServer
import pyd2bot.thriftServer.pyd2botService.Pyd2botService as Pyd2botService
from pyd2bot.thriftServer.HttpRequestHandler import getReqHandler
from pyd2bot.thriftServer.pyd2botServer import Pyd2botServer
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

if __name__ == "__main__":
    import argparse
    from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", help="the server host", type=str, default="0.0.0.0")
    parser.add_argument("--port", help="the server port", type=int, default=9999)
    parser.add_argument("--id", help="the server id", type=str, default="unknown")
    args = parser.parse_args()
    Logger.prefix = args.id
    Logger("Pyd2BotServer", True)
    handler = Pyd2botServer(args.id)
    processor = Pyd2botService.Processor(handler)
    serverTransport = THttpServer.THttpServer(processor, (args.host, args.port), TJSONProtocolFactory())
    serverTransport.httpd.RequestHandlerClass = getReqHandler(serverTransport)
    Logger().info(f"[Server - {args.id}] Started serving on {args.host}:{args.port}")
    serverTransport.serve()
