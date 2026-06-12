"""
Unit tests for the Ladder logic evaluator and scan cycle.
"""
import pytest
from engine.tags import DIGITAL_INPUTS, DIGITAL_OUTPUTS, MEMORY_BITS
from engine.scan_cycle import ScanCycle


@pytest.fixture
def reset_tags():
    """Reset all tags to their initial state before each test."""
    for tag in DIGITAL_INPUTS:
        DIGITAL_INPUTS[tag] = False
    for tag in DIGITAL_OUTPUTS:
        DIGITAL_OUTPUTS[tag] = False
    for tag in MEMORY_BITS:
        MEMORY_BITS[tag] = False


def test_simple_no_contact(reset_tags):
    """A single NO contact: motor on when START is pressed."""
    program = {
        "rungs": [
            {
                "contacts": [{"tag": "START_BUTTON", "type": "NO"}],
                "coil": "MOTOR_MAIN",
            }
        ]
    }
    engine = ScanCycle(program=program, scan_time=0.01)

    # Start button pressed
    DIGITAL_INPUTS["START_BUTTON"] = True
    engine._execute_ladder()
    assert DIGITAL_OUTPUTS["MOTOR_MAIN"] is True

    # Start button released
    DIGITAL_INPUTS["START_BUTTON"] = False
    engine._execute_ladder()
    assert DIGITAL_OUTPUTS["MOTOR_MAIN"] is False


def test_nc_contact(reset_tags):
    """A single NC contact: motor on when STOP is NOT pressed."""
    program = {
        "rungs": [
            {
                "contacts": [{"tag": "STOP_BUTTON", "type": "NC"}],
                "coil": "MOTOR_MAIN",
            }
        ]
    }
    engine = ScanCycle(program=program, scan_time=0.01)

    # STOP not pressed → motor should be on
    DIGITAL_INPUTS["STOP_BUTTON"] = False
    engine._execute_ladder()
    assert DIGITAL_OUTPUTS["MOTOR_MAIN"] is True

    # STOP pressed → motor should be off
    DIGITAL_INPUTS["STOP_BUTTON"] = True
    engine._execute_ladder()
    assert DIGITAL_OUTPUTS["MOTOR_MAIN"] is False


def test_series_and(reset_tags):
    """Two NO contacts in series: motor on only when both inputs are True."""
    program = {
        "rungs": [
            {
                "contacts": [
                    {"tag": "START_BUTTON", "type": "NO"},
                    {"tag": "PART_SENSOR", "type": "NO"},
                ],
                "coil": "CONVEYOR_MOTOR",
            }
        ]
    }
    engine = ScanCycle(program=program, scan_time=0.01)

    # Both off
    DIGITAL_INPUTS["START_BUTTON"] = False
    DIGITAL_INPUTS["PART_SENSOR"] = False
    engine._execute_ladder()
    assert DIGITAL_OUTPUTS["CONVEYOR_MOTOR"] is False

    # Only one on
    DIGITAL_INPUTS["START_BUTTON"] = True
    engine._execute_ladder()
    assert DIGITAL_OUTPUTS["CONVEYOR_MOTOR"] is False

    # Both on
    DIGITAL_INPUTS["PART_SENSOR"] = True
    engine._execute_ladder()
    assert DIGITAL_OUTPUTS["CONVEYOR_MOTOR"] is True


def test_emergency_stop(reset_tags):
    """E‑STOP overrides all ladder logic and kills all outputs."""
    program = {
        "rungs": [
            {
                "contacts": [{"tag": "START_BUTTON", "type": "NO"}],
                "coil": "MOTOR_MAIN",
            }
        ]
    }
    engine = ScanCycle(program=program, scan_time=0.01)

    # Motor running normally
    DIGITAL_INPUTS["START_BUTTON"] = True
    engine._execute_ladder()
    assert DIGITAL_OUTPUTS["MOTOR_MAIN"] is True

    # E‑STOP kills it
    DIGITAL_INPUTS["EMERGENCY_STOP"] = True
    engine._emergency_shutdown()
    assert DIGITAL_OUTPUTS["MOTOR_MAIN"] is False


def test_ton_timer():
    """TON output should go True after the preset time with continuous input."""
    from engine.timers import TON
    ton = TON(preset=0.5)

    # Keep input True for the full preset
    for _ in range(10):
        ton.update(True, 0.1)
    assert ton.done is True
    assert ton.accumulated >= 0.5


def test_ton_reset():
    """TON should reset accumulated time when input goes False."""
    from engine.timers import TON
    ton = TON(preset=0.5)
    ton.update(True, 0.3)
    ton.update(False, 0.1)
    assert ton.accumulated == 0.0
    assert ton.done is False


def test_memory_bit_latching(reset_tags):
    """Motor stays on after START is released (latching with OR contact)."""
    program = {
        "rungs": [
            {
                "contacts": [
                    [
                        {"tag": "START_BUTTON", "type": "NO"},
                        {"tag": "STOP_BUTTON", "type": "NC"},
                    ],
                    [
                        {"tag": "MOTOR_MAIN", "type": "NO"},
                        {"tag": "STOP_BUTTON", "type": "NC"},
                    ],
                ],
                "coil": "MOTOR_MAIN",
            }
        ]
    }
    engine = ScanCycle(program=program, scan_time=0.01)

    # Pulse START
    DIGITAL_INPUTS["START_BUTTON"] = True
    engine._execute_ladder()
    assert DIGITAL_OUTPUTS["MOTOR_MAIN"] is True

    # Release START – motor should stay on (seal)
    DIGITAL_INPUTS["START_BUTTON"] = False
    engine._execute_ladder()
    assert DIGITAL_OUTPUTS["MOTOR_MAIN"] is True

    # Press STOP – motor should turn off
    DIGITAL_INPUTS["STOP_BUTTON"] = True
    engine._execute_ladder()
    assert DIGITAL_OUTPUTS["MOTOR_MAIN"] is False

def test_ctu_counts_up():
    from engine.counters import CTU
    ctu = CTU(preset=3)
    # Simulate 5 rising edges
    for _ in range(5):
        ctu.update(True)
        ctu.update(False)
    assert ctu.accumulated == 3
    assert ctu.done is True

def test_ctu_reset():
    from engine.counters import CTU
    ctu = CTU(preset=5)
    ctu.update(True)
    ctu.update(False)
    ctu.update(True)
    ctu.update(False)
    ctu.update(True, reset_signal=True)
    assert ctu.accumulated == 0
    assert ctu.done is False