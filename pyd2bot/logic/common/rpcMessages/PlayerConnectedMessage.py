class PlayerConnectedMessage:
    
    def __init__(self, instance) -> None:
        self.instanceId = instance
    
    def __str__(self) -> str:
        return f"BotConnect({self.instanceId})"