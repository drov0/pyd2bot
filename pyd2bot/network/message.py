import logging
from ..utils.binaryIO import ByteArray, Buffer
from .protocol import DofusProtocol
from . import msgReceiver

logger = logging.getLogger("labot")


class Message:
    protocol = DofusProtocol()
    
    def __init__(self, m_id, data, count=None, from_client=None, src=None, dst=None):
        self.id = m_id
        self.data = data
        self.count = count
        self.from_client = from_client
        self.src_ip = src
        self.dst_ip = dst

    def __str__(self):
        ans = str.format(
            "{}(m_id={}, data={}, count={})",
            self.__class__.__name__,
            self.id,
            self.data,
            self.count,
        )
        return ans

    def __repr__(self):
        ans = str.format(
            "{}(m_id={}, data={!r}, count={})",
            self.__class__.__name__,
            self.id,
            self.data,
            self.count,
        )
        return ans

    @staticmethod
    def fromRaw(buf: Buffer, from_client, src=None, dst=None):
        """Read a message from the buffer and
        empty the beginning of the buffer.
        msg fields spec: 
            id     |   len    |   data
           2 bits  |  2 bits  |  len bits
        """
        if not buf:
            return
        try:
            header = buf.readUnsignedShort()
            if from_client:
                count = buf.readUnsignedInt()
            else:
                count = None
            lenData = int.from_bytes(buf.read(header & 3), "big")
            id = header >> 2
            data = ByteArray(buf.read(lenData))
        except IndexError:
            buf.position = 0
            return None

        if id == 2:
            newbuffer = Buffer(data.readByteArray())
            newbuffer.uncompress()
            msg = Message.fromRaw(newbuffer, from_client)
            if not msg or newbuffer.remaining():
                raise Exception("Unable to parse Message")
            return msg
        
        buf.end()

        return Message(m_id=id, 
                   data=data, 
                   count=count, 
                   from_client=from_client,
                   src=src,
                   dst=dst)

    def lenlenData(self):
        if len(self.data) > 65535:
            return 3
        if len(self.data) > 255:
            return 2
        if len(self.data) > 0:
            return 1
        return 0

    def bytes(self):
        header = 4 * self.id + self.lenlenData()
        ans = ByteArray()
        ans.writeUnsignedShort(header)
        if self.count is not None:
            ans.writeUnsignedInt(self.count)
        ans += len(self.data).to_bytes(self.lenlenData(), "big")
        ans += self.data
        return ans

    @property
    def name(self):
        if not self.from_client:
            return msgReceiver._messagesTypes[self.id]
        else:
            return self.protocol.getMsgById(self.id)["name"]

    def json(self):
        if not hasattr(self, "parsed"):
            self.parsed = self.protocol.read(self.name, self.data)
        return self.parsed

    @staticmethod
    def from_json(json, count=None, random_hash=True):
        type_name: str = json["__type__"]
        msg_type: dict = Message.protocol.getMsgTypeByName(type_name)
        type_id: int = msg_type["protocolId"]
        data = Message.protocol.write(type_name, json, random_hash=random_hash)
        return Message(type_id, data, count)
