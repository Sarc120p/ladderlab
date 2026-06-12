"""
LadderLab – Timer implementations (TON, TOF).
Each timer is updated once per scan cycle with the elapsed time.
"""

class TON:
    """Timer On‑Delay: output goes True after the input has been True for 'preset' seconds."""
    def __init__(self, preset: float = 5.0):
        self.preset = preset
        self.accumulated = 0.0
        self.done = False

    def update(self, input_signal: bool, elapsed: float):
        if input_signal:
            self.accumulated = min(self.preset, self.accumulated + elapsed)
        else:
            self.accumulated = 0.0
        self.done = self.accumulated >= self.preset

class TOF:
    """Timer Off‑Delay: output goes False after the input has been False for 'preset' seconds."""
    def __init__(self, preset: float = 3.0):
        self.preset = preset
        self.accumulated = 0.0
        self.done = True   # starts True because input is typically True initially

    def update(self, input_signal: bool, elapsed: float):
        if not input_signal:
            self.accumulated = min(self.preset, self.accumulated + elapsed)
        else:
            self.accumulated = 0.0
        self.done = not (self.accumulated >= self.preset)