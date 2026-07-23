import math

import pytest

from dynamic_ac_generator.config import SimulationConfig


def test_default_config_calculates_phase_impedances() -> None:
    config = SimulationConfig()

    assert config.CONTROL_MODE == "unregulated"
    assert math.isclose(config.SIMULATION_TIME_S, 100.0, rel_tol=1e-12)
    assert math.isclose(config.DAMPING_COMPARISON_SIMULATION_TIME_S, 100.0, rel_tol=1e-12)
    assert math.isclose(config.phase_voltage_rms, 400.0 / math.sqrt(3.0), rel_tol=1e-12)
    assert math.isclose(abs(config.initial_impedance_ohm), 0.8, rel_tol=1e-12)
    assert math.isclose(math.degrees(math.atan2(config.initial_impedance_ohm.imag, config.initial_impedance_ohm.real)), -45.0, rel_tol=1e-12)
    assert math.isclose(abs(config.first_step_impedance_ohm), 1.28, rel_tol=1e-12)
    assert math.isclose(abs(config.second_step_impedance_ohm), 0.96, rel_tol=1e-12)
    assert math.isclose(abs(config.final_impedance_ohm), abs(config.initial_impedance_ohm), rel_tol=1e-12)
    assert config.load_schedule == (
        (0.0, 0.5, -45.0),
        (10.0, 0.8, -30.0),
        (40.0, 0.6, -60.0),
        (70.0, 0.5, -45.0),
    )
    assert config.load_step_times_s == (10.0, 40.0, 70.0)
    assert math.isclose(config.final_load_pu, config.INITIAL_LOAD_PU, rel_tol=1e-12)
    assert math.isclose(config.final_load_angle_deg, config.INITIAL_LOAD_ANGLE_DEG, rel_tol=1e-12)


def test_config_rejects_invalid_load_step_time() -> None:
    with pytest.raises(ValueError, match="Load step time"):
        SimulationConfig(LOAD_STEP_TIME_S=10.0, SIMULATION_TIME_S=10.0)


def test_config_rejects_unknown_control_mode() -> None:
    with pytest.raises(ValueError, match="Control mode"):
        SimulationConfig(CONTROL_MODE="droop")
