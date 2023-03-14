class MuleSwitchedToCombatContext:
    
    def __init__(self, muleId):
        self.muleId = muleId
    
    def __str__(self) -> str:
        return f"MuleSwitchedToCombat({self.muleId})"
