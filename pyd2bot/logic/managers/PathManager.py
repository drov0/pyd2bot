from pyd2bot.models.farmPaths.RandomSubAreaFarmPath import RandomSubAreaFarmPath

class PathManager:
    _pathClass = {
        "RandomSubAreaFarmPath": RandomSubAreaFarmPath,
    }

    
    @classmethod
    def from_json(cls, json_obj):
        pathCls = cls._pathClass.get(json_obj["type"])
        if pathCls:
            return pathCls.from_json(json_obj)
        raise Exception("Unknown path type: " + json_obj["type"])


if __name__ == "__main__":
    pass
