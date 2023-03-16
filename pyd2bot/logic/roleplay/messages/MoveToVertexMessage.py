from pydofus2.com.ankamagames.dofus.modules.utils.pathFinding.world.Vertex import \
    Vertex
from pydofus2.com.ankamagames.jerakine.messages.Message import Message


class MoveToVertexMessage(Message):
    def __init__(self, Vertex: Vertex):
        self.vertex = Vertex
