class SellerVacantMessage:
    
    def __init__(self, instanceId) -> None:
        self.instanceId = instanceId
        
    def __str__(self):
        return f"SellerVacant({self.instanceId})"