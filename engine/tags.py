"""
LadderLab – Tag memory map for the PLC engine.
Defines digital inputs, outputs, internal memory bits,
timers and counters with their initial values.
"""

from __future__ import annotations

from .counters import CTD, CTU
from .timers import TOF, TON

# ---------------------------------------------------------------------------
# Digital Inputs (read-only from the engine's perspective)
# ---------------------------------------------------------------------------
DIGITAL_INPUTS: dict[str, bool] = {
    "START_BUTTON": False,
    "STOP_BUTTON": False,
    "EMERGENCY_STOP": False,
    "PART_SENSOR": False,        # activated by conveyor animation
    "END_LIMIT_SWITCH": False,   # end-of-track limit switch
    "LEVEL_SENSOR": False,       # tank level sensor
    "TEMPERATURE_SENSOR": False,
}

# ---------------------------------------------------------------------------
# Digital Outputs (written by the engine)
# ---------------------------------------------------------------------------
DIGITAL_OUTPUTS: dict[str, bool] = {
    "MOTOR_MAIN": False,         # main motor (agitator / pump)
    "CONVEYOR_MOTOR": False,     # conveyor belt motor
    "ALARM_LIGHT": False,
    "VALVE_OPEN": False,         # tank fill valve
    "GREEN_LAMP": False,
    "RED_LAMP": False,
}

# ---------------------------------------------------------------------------
# Internal Memory Bits (used for intermediate logic)
# ---------------------------------------------------------------------------
MEMORY_BITS: dict[str, bool] = {
    "M0": False,
    "M1": False,
    "M2": False,
    "M3": False,
    "M4": False,
}

# ---------------------------------------------------------------------------
# Timers (TON / TOF)
# ---------------------------------------------------------------------------
TIMERS: dict[str, dict] = {
    "TON_MOTOR_DELAY": {
        "instance": TON(5.0),
        "input_tag": "MOTOR_MAIN",
    },
    "TOF_MOTOR_OFF": {
        "instance": TOF(3.0),
        "input_tag": "MOTOR_MAIN",
    },
    "TON_CONVEYOR_DELAY": {
        "instance": TON(3.0),
        "input_tag": "CONVEYOR_MOTOR",
    },
}

# ---------------------------------------------------------------------------
# Counters (CTU / CTD)
# ---------------------------------------------------------------------------
COUNTERS: dict[str, dict] = {
    "CTU_PART_COUNT": {
        "instance": CTU(10),        # preset = 10
        "input_tag": "PART_SENSOR",
    },
    "CTD_BATCH_COUNT": {
        "instance": CTD(5),
        "input_tag": "MOTOR_MAIN",
    },
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_all_tags() -> dict:
    """
    Return a single dict with every tag and its current value.

    The returned dict is suitable for the dashboard and WebSocket updates.
    Timer and counter accumulated values are included as `{name}_ACC`.
    """
    all_tags: dict[str, bool | float | int] = {}
    all_tags.update(DIGITAL_INPUTS)
    all_tags.update(DIGITAL_OUTPUTS)
    all_tags.update(MEMORY_BITS)

    for name, timer_data in TIMERS.items():
        timer = timer_data["instance"]
        all_tags[name] = timer.done
        all_tags[f"{name}_ACC"] = round(timer.accumulated, 2)

    for name, counter_data in COUNTERS.items():
        counter = counter_data["instance"]
        all_tags[name] = counter.done
        # counters are integers by nature, but ensure int just in case
        all_tags[f"{name}_ACC"] = int(counter.accumulated)

    return all_tags


def reset_all_tags() -> None:
    """
    Reset every tag to its initial (power‑off) state.
    Useful when loading a new program or after an emergency stop reset.
    """
    for tag in DIGITAL_INPUTS:
        DIGITAL_INPUTS[tag] = False
    for tag in DIGITAL_OUTPUTS:
        DIGITAL_OUTPUTS[tag] = False
    for tag in MEMORY_BITS:
        MEMORY_BITS[tag] = False

    for timer_data in TIMERS.values():
        timer_data["instance"].accumulated = 0.0
        timer_data["instance"].done = False
        # TON/TOF specific reset (TON: done=False, accumulated=0; TOF: done=True, accumulated=0)
        if isinstance(timer_data["instance"], TOF):
            timer_data["instance"].done = True

    for counter_data in COUNTERS.values():
        counter_data["instance"].accumulated = 0
        counter_data["instance"].done = False
        counter_data["instance"]._prev_input = False
        # reset CTD to preset?
        if isinstance(counter_data["instance"], CTD):
            counter_data["instance"].accumulated = counter_data["instance"].preset