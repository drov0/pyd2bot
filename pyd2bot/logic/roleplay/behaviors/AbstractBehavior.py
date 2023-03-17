from enum import Enum
import threading
from pydofus2.com.ankamagames.berilia.managers.EventsHandler import Listener
from pydofus2.com.ankamagames.berilia.managers.KernelEventsManager import KernelEventsManager
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger
from pydofus2.com.ankamagames.jerakine.metaclasses.Singleton import Singleton

class AbstractBehaviorState(Enum):
    UNKNOWN = 0
    RUNNING = 1
    IDLE = 2
class AbstractBehavior(metaclass=Singleton):
    ALREADY_RUNNING = 666
    
    def __init__(self) -> None:
        self.running = threading.Event()
        self.callback = None
        self.endListeners = []
        self.state = AbstractBehaviorState.UNKNOWN
        super().__init__()

    def start(self, *args, **kwargs) -> None:
        raise NotImplementedError("Abstract method.")

    def onFinish(self, callback):
        self.endListeners.append(callback)

    def finish(self, status: bool, error: str = None, **kwargs) -> None:
        if not self.running.is_set():
            return Logger().warning(f"[{type(self).__name__}] wants to finish but not running!")
        Logger().info(f"[{type(self).__name__}] Finished.")
        callback = self.callback
        self.callback = None
        self.running.clear()
        type(self).clear()
        KernelEventsManager().clearAllByOrigin(self)
        from pyd2bot.misc.BotEventsmanager import BotEventsManager
        BotEventsManager().clearAllByOrigin(self)
        error = f"[{type(self).__name__}] failed for reason : {error}" if error else None
        if callback:
            callback(status, error, **kwargs)
        else:
            Logger().debug(error)
        if self.endListeners:
            for callback in self.endListeners:
                callback(status, error)
    
    @property
    def listeners(self) -> list[Listener]:
        from pyd2bot.misc.BotEventsmanager import BotEventsManager
        return KernelEventsManager().getListenersByOrigin(self) + BotEventsManager().getListenersByOrigin(self)

    def isRunning(self):
        return self.running.is_set()
    
    def getState(self):
        return AbstractBehaviorState.RUNNING.name if self.isRunning() else AbstractBehaviorState.IDLE.name

    def __str__(self) -> str:
        listeners = [str(listener) for listener in self.listeners]
        return f"{type(self).__name__} ({self.getState()}), Listeners: {listeners}"
