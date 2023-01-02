from pydofus2.com.ankamagames.jerakine.messages.Message import Message


class AutoTripEndedMessage(Message):
    def __init__(self, mapId):
        self.mapId = mapId
