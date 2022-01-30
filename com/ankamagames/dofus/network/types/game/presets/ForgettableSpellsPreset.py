from com.ankamagames.dofus.network.types.game.presets.Preset import Preset
from com.ankamagames.dofus.network.types.game.presets.SpellsPreset import SpellsPreset
from com.ankamagames.dofus.network.types.game.presets.SpellForPreset import SpellForPreset


class ForgettableSpellsPreset(Preset):
    protocolId = 8231
    baseSpellsPreset:SpellsPreset
    forgettableSpells:SpellForPreset
    
    