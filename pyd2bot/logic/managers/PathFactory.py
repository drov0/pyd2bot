from pyd2bot.models.farmPaths.RandomAreaFarmPath import RandomAreaFarmPath
from pyd2bot.models.farmPaths.RandomSubAreaFarmPath import RandomSubAreaFarmPath
from pyd2bot.thriftServer.pyd2botService.ttypes import PathType, Path


class PathFactory:
    _pathClass = {
        PathType.RandomSubAreaFarmPath: RandomSubAreaFarmPath,
        PathType.RandomAreaFarmPath: RandomAreaFarmPath
    }

    @classmethod
    def from_thriftObj(cls, obj: Path):
        if not isinstance(obj, Path):
            raise ValueError("session.path must be a Path instance")
        if obj.type not in cls._pathClass:
            raise ValueError("Unknown path type: " + str(obj.type))
        pathCls = cls._pathClass.get(obj.type)
        return pathCls.from_thriftObj(obj)
