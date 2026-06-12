"""
LadderLab – Alarm Manager
Evaluates system conditions every scan cycle and generates
timestamped events with severity levels (info, warning, critical).
"""

from datetime import datetime, timezone
from typing import List, Dict, Optional


class AlarmManager:
    SEVERITY_INFO = "info"
    SEVERITY_WARNING = "warning"
    SEVERITY_CRITICAL = "critical"

    # ------------------------------------------------------------------
    # Configurable thresholds (adjust as needed)
    # ------------------------------------------------------------------
    MOTOR_OVERRUN_TIME = 5.0        # seconds of continuous motor run
    SENSOR_TIMEOUT_TIME = 3.0       # seconds without sensor detection while motor on

    def __init__(self):
        # Event history
        self.events: List[Dict] = []

        # Internal state accumulators
        self._motor_on_time = 0.0
        self._sensor_inactive_time = 0.0

        # Latch flags to prevent duplicate alarms
        self._overrun_triggered = False
        self._timeout_triggered = False
        self._counter_overflowed = False
        self._tank_critical_triggered = False
        self._tank_low_triggered = False

    # ------------------------------------------------------------------
    # Public API (used by scan cycle)
    # ------------------------------------------------------------------
    def evaluate(self, tags: Dict[str, bool | float | int], scan_time: float) -> List[Dict]:
        """
        Called once per scan cycle.
        Returns a list of new alarm events generated during this cycle.
        """
        new_events = []

        # ---- Convenience variables ----
        motor_on = tags.get("CONVEYOR_MOTOR", False) or tags.get("MOTOR_MAIN", False)
        part_sensor = tags.get("PART_SENSOR", False)
        level_sensor = tags.get("LEVEL_SENSOR", False)
        valve_open = tags.get("VALVE_OPEN", False)

        # ================================================================
        # 1. Motor Overrun
        # ================================================================
        if motor_on:
            self._motor_on_time += scan_time
        else:
            self._motor_on_time = 0.0
            self._overrun_triggered = False

        if self._motor_on_time > self.MOTOR_OVERRUN_TIME and not self._overrun_triggered:
            new_events.append(self._create_event(
                f"Motor overrun: running continuously for >{self.MOTOR_OVERRUN_TIME:.0f} s",
                self.SEVERITY_WARNING,
            ))
            self._overrun_triggered = True

        # ================================================================
        # 2. Sensor Timeout
        # ================================================================
        if motor_on and not part_sensor:
            self._sensor_inactive_time += scan_time
        else:
            self._sensor_inactive_time = 0.0
            self._timeout_triggered = False

        if self._sensor_inactive_time > self.SENSOR_TIMEOUT_TIME and not self._timeout_triggered:
            new_events.append(self._create_event(
                f"Sensor timeout: no part detected for >{self.SENSOR_TIMEOUT_TIME:.0f} s",
                self.SEVERITY_WARNING,
            ))
            self._timeout_triggered = True

        # ================================================================
        # 3. Counter Overflow (CTU reaches preset)
        # ================================================================
        if tags.get("CTU_PART_COUNT", False) and not self._counter_overflowed:
            new_events.append(self._create_event(
                "Part counter (CTU) reached preset value (10)",
                self.SEVERITY_INFO,
            ))
            self._counter_overflowed = True
        if not tags.get("CTU_PART_COUNT", False):
            self._counter_overflowed = False

        # ================================================================
        # 4. Tank Critical – level high while valve still open
        # ================================================================
        if level_sensor and valve_open:
            if not self._tank_critical_triggered:
                new_events.append(self._create_event(
                    "Tank level high while fill valve is still open!",
                    self.SEVERITY_CRITICAL,
                ))
                self._tank_critical_triggered = True
        else:
            self._tank_critical_triggered = False

        # ================================================================
        # 5. Tank Low Warning – motor on but level sensor false
        # ================================================================
        if motor_on and not level_sensor and tags.get("MOTOR_MAIN", False):
            if not self._tank_low_triggered:
                new_events.append(self._create_event(
                    "Tank level low: agitator running with insufficient level",
                    self.SEVERITY_WARNING,
                ))
                self._tank_low_triggered = True
        else:
            self._tank_low_triggered = False

        # Store and return
        self.events.extend(new_events)
        return new_events

    # ------------------------------------------------------------------
    # Manual triggers
    # ------------------------------------------------------------------
    def trigger(self, message: str, severity: str = "warning") -> Dict:
        """Manually record an alarm (e.g., from emergency shutdown)."""
        return self._create_event(message, severity)

    def emergency_shutdown(self, affected_outputs: List[str]) -> List[Dict]:
        """Record a critical event for each output de‑energized by E‑STOP."""
        events = []
        for tag in affected_outputs:
            events.append(self._create_event(
                f"Output {tag} de-energized by E‑STOP",
                self.SEVERITY_CRITICAL,
            ))
        return events

    # ------------------------------------------------------------------
    # History retrieval
    # ------------------------------------------------------------------
    def get_recent(self, limit: int = 50) -> List[Dict]:
        """Return the most recent events (newest first)."""
        return list(reversed(self.events[-limit:]))

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------
    def _create_event(self, message: str, severity: str) -> Dict:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "alarm",
            "severity": severity,
            "message": message,
        }