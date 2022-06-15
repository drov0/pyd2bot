from whistle import Event
from pydofus2.com.ankamagames.jerakine.sequencer.ISequencable import ISequencable
from pydofus2.com.ankamagames.jerakine.sequencer.ISequencer import ISequencer


class SequencerEvent(Event):

    SEQUENCE_END: str = "onSequenceEnd"

    SEQUENCE_STEP_START: str = "SEQUENCE_STEP_START"

    SEQUENCE_STEP_FINISH: str = "SEQUENCE_STEP_FINISH"

    SEQUENCE_TIMEOUT: str = "onSequenceTimeOut"

    _sequencer: ISequencer

    _step: ISequencable

    def __init__(self, type: str, sequencer: ISequencer = None, step: ISequencable = None):
        super().__init__()
        self.type = type
        self._sequencer = sequencer
        self._step = step

    @property
    def sequencer(self) -> ISequencer:
        return self._sequencer

    @property
    def step(self) -> ISequencable:
        return self._step
