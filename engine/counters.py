"""
LadderLab – Counter implementations (CTU, CTD).
Each counter is updated once per scan cycle by detecting rising edges.
"""

class CTU:
    """Count Up: increments on rising edge of input signal."""
    def __init__(self, preset: int = 10):
        self.preset = preset
        self.accumulated = 0
        self.done = False
        self._prev_input = False  # for edge detection

    def update(self, input_signal: bool, reset_signal: bool = False):
        # Reset has priority
        if reset_signal:
            self.accumulated = 0
            self.done = False
            self._prev_input = input_signal
            return

        # Rising edge detection (False → True)
        if input_signal and not self._prev_input:
            self.accumulated = min(self.preset, self.accumulated + 1)

        self._prev_input = input_signal
        self.done = self.accumulated >= self.preset


class CTD:
    """Count Down: decrements on rising edge of input signal."""
    def __init__(self, preset: int = 5):
        self.preset = preset
        self.accumulated = preset  # starts at preset
        self.done = False
        self._prev_input = False

    def update(self, input_signal: bool, reset_signal: bool = False):
        if reset_signal:
            self.accumulated = self.preset
            self.done = False
            self._prev_input = input_signal
            return

        if input_signal and not self._prev_input:
            self.accumulated = max(0, self.accumulated - 1)

        self._prev_input = input_signal
        self.done = self.accumulated <= 0