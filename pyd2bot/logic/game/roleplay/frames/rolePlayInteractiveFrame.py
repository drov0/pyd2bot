from pyd2bot.logic import IFrame
import logging
logger = logging.getLogger("bot")


class RolePlayInteractiveFrame(IFrame):


    def process(self, msg) -> bool:
        mtype = msg["__type__"]
        
        if mtype == "InteractiveUseErrorMessage":
            self.bot.farmingError.set()
            return True
        
        elif mtype == "InteractiveUsedMessage":
            skill = msg["skillId"]
            self.bot.currFarmingElem = msg["elemId"]
            logger.info(f"Farming animation of elem {self.bot.currFarmingElem} with skill {skill} started")
            self.bot.farming.set()
            return True
        
        elif mtype == "InteractiveUseEndedMessage":
            logger.info(f"Farming animation of elem {self.bot.currFarmingElem} ended")            
            self.bot.currFarmingElem = None
            self.bot.farming.clear()
            return True
    
        elif mtype == "StatedElementUpdatedMessage":
            elem_id = msg["statedElement"]["elementId"]
            self.bot.currMapStatedElems[elem_id] = msg["statedElement"]
            logger.info(f"Element {elem_id} state changed")
            return True
        
        elif mtype == "InteractiveElementUpdatedMessage":
            elem_id = msg["interactiveElement"]["elementId"]
            self.bot.currMapInteractiveElems[elem_id] = msg["interactiveElement"]
            logger.info(f"Element {elem_id} interactiveness changed")
            return True
        
        return False