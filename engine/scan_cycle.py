"""
LadderLab – PLC scan cycle implementation.
Runs continuously, reading inputs, executing the Ladder program,
updating outputs, timers, counters, evaluating alarms and publishing state changes.
"""
import time
import threading
from datetime import datetime, timezone
from typing import Callable, Optional

from .tags import DIGITAL_INPUTS, DIGITAL_OUTPUTS, MEMORY_BITS, TIMERS, COUNTERS
from .ladder_executor import LadderExecutor
from .alarm_manager import AlarmManager


class ScanCycle:
    """
    Simulates a PLC scan cycle.
    Runs on its own thread at a configurable frequency.
    """

    def __init__(
        self,
        program: Optional[dict] = None,
        scan_time: float = 0.1,
        on_update: Optional[Callable[[dict], None]] = None,
        on_event: Optional[Callable[[str, str, Optional[str]], None]] = None,
    ):
        self.program = program or {"rungs": []}
        self.scan_time = scan_time
        self.on_update = on_update          # callback(AllTags) – called after each scan
        self.on_event = on_event            # callback(event_type, message, severity) – for persistence
        self.alarm_manager = AlarmManager()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.event_log: list[dict] = []

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    def start(self):
        """Start the scan cycle in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the scan cycle gracefully."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def load_program(self, program: dict):
        """Load a new Ladder program (JSON with 'rungs' list)."""
        self.program = program or {"rungs": []}

    def force_input(self, tag: str, value: bool):
        """Force a digital input to a specific value."""
        if tag in DIGITAL_INPUTS:
            DIGITAL_INPUTS[tag] = value

    def get_event_log(self) -> list[dict]:
        """Return the event log (most recent first)."""
        return list(reversed(self.event_log[-50:]))

    # ------------------------------------------------------------
    # Private implementation
    # ------------------------------------------------------------
    def _run(self):
        """Main scan loop (runs on background thread)."""
        while self._running:
            cycle_start = time.perf_counter()

            # Emergency stop takes priority over everything
            if DIGITAL_INPUTS.get("EMERGENCY_STOP", False):
                self._emergency_shutdown()
            else:
                self._execute_ladder()

            # Publish state via callback (WebSocket broadcast)
            if self.on_update:
                self._publish_state()

            # Maintain scan frequency
            elapsed = time.perf_counter() - cycle_start
            sleep_time = max(0, self.scan_time - elapsed)
            time.sleep(sleep_time)

    def _execute_ladder(self):
        """
        Evaluate every rung, buffering writes, update timers/counters,
        and then evaluate alarms.
        """
        pending_writes: dict[str, bool] = {}

        def write_tag(tag: str, value: bool):
            if tag in DIGITAL_OUTPUTS or tag in MEMORY_BITS:
                pending_writes[tag] = value

        def read_tag(tag: str) -> bool:
            # 1. Buffered writes (simulates immediate I/O update)
            if tag in pending_writes:
                return pending_writes[tag]
            # 2. Digital inputs
            if tag in DIGITAL_INPUTS:
                return DIGITAL_INPUTS[tag]
            # 3. Digital outputs (current state, not yet overwritten by this scan)
            if tag in DIGITAL_OUTPUTS:
                return DIGITAL_OUTPUTS[tag]
            # 4. Memory bits
            if tag in MEMORY_BITS:
                return MEMORY_BITS[tag]
            # 5. Timer done status
            if tag in TIMERS:
                return TIMERS[tag]["instance"].done
            # 6. Counter done status
            if tag in COUNTERS:
                return COUNTERS[tag]["instance"].done
            return False

        # Delegate Ladder evaluation to the executor
        LadderExecutor.evaluate_rungs(
            self.program.get("rungs", []), read_tag, write_tag
        )

        # Apply writes to the actual dictionaries
        for tag, value in pending_writes.items():
            self._set_tag_value(tag, value)

        # Update timers
        for name, timer_data in TIMERS.items():
            timer = timer_data["instance"]
            input_signal = self._get_tag_value(timer_data["input_tag"])
            timer.update(input_signal, self.scan_time)

        # Update counters
        for name, counter_data in COUNTERS.items():
            counter = counter_data["instance"]
            input_signal = self._get_tag_value(counter_data["input_tag"])
            counter.update(input_signal, reset_signal=False)

        # ---- Evaluate alarms after this scan ----
        from .tags import get_all_tags
        tags_snapshot = get_all_tags()
        alarm_events = self.alarm_manager.evaluate(tags_snapshot, self.scan_time)
        self.event_log.extend(alarm_events)

        # Notify external persistence callback
        if self.on_event:
            for evt in alarm_events:
                self.on_event(evt["type"], evt["message"], evt.get("severity"))

    def _emergency_shutdown(self):
        """De-energize all outputs and log critical alarm events."""
        affected = []
        for tag in DIGITAL_OUTPUTS:
            if DIGITAL_OUTPUTS[tag]:
                DIGITAL_OUTPUTS[tag] = False
                affected.append(tag)

        if affected:
            # Use alarm_manager to generate standardized critical events
            alarm_events = self.alarm_manager.emergency_shutdown(affected)
            self.event_log.extend(alarm_events)

            if self.on_event:
                for evt in alarm_events:
                    self.on_event(evt["type"], evt["message"], evt.get("severity"))

    def _get_tag_value(self, tag: str) -> bool:
        """Look up the current value of any tag (for non‑buffered reads)."""
        if tag in DIGITAL_INPUTS:
            return DIGITAL_INPUTS[tag]
        if tag in DIGITAL_OUTPUTS:
            return DIGITAL_OUTPUTS[tag]
        if tag in MEMORY_BITS:
            return MEMORY_BITS[tag]
        if tag in TIMERS:
            return TIMERS[tag]["instance"].done
        if tag in COUNTERS:
            return COUNTERS[tag]["instance"].done
        return False

    def _set_tag_value(self, tag: str, value: bool):
        """Set the value of a writable tag (output or memory bit)."""
        if tag in DIGITAL_OUTPUTS:
            DIGITAL_OUTPUTS[tag] = value
        elif tag in MEMORY_BITS:
            MEMORY_BITS[tag] = value

    def _publish_state(self):
        """Invoke the on_update callback with the full tag dict."""
        from .tags import get_all_tags
        if self.on_update:
            self.on_update(get_all_tags())