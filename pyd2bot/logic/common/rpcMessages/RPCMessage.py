import threading
import uuid
from time import perf_counter


class RPCMessage:
    def __init__(self, dst: str, data=None) -> None:
        self.oneway = None
        self.uid = uuid.uuid1()
        self.creationTime = perf_counter()
        self.reqUid = None
        self.sender = threading.current_thread().name
        self.dest = dst
        self.data = data

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.sender}, {self.dest}, {self.data})"