from pydofus2.com.ankamagames.jerakine.metaclasses.Singleton import Singleton
from whistle import EventDispatcher


class BotEventsManager(EventDispatcher, metaclass=Singleton):

    MEMBERS_READY = 0

    def __init__(self):
        super().__init__()
