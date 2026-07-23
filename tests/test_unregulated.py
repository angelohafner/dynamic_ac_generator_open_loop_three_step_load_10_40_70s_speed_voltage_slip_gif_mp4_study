import math
import numpy as np

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.simulation import DynamicSimulation


def test_unregulated_initial_state_is_60_hz_with_first_load() -> None:
    config = SimulationConfig(CONTROL_MODE="unregulated")
    results = DynamicSimulation(config).run()

    assert math.isclose(results.frequency_hz[0], 60.0, abs_tol=1e-9)
    assert math.isclose(results.mechanical_power_pu[0], config.initial_active_power_pu, abs_tol=1e-9)
    assert math.isclose(results.electrical_power_pu[0], config.initial_active_power_pu, abs_tol=1e-9)


def test_unregulated_speed_derivative_matches_swing_equation_after_load_step() -> None:
    config = SimulationConfig(CONTROL_MODE="unregulated")
    results = DynamicSimulation(config).run()
    index = int(np.searchsorted(results.time_s, config.LOAD_STEP_TIME_S + 0.02))

    measured_derivative = (
        results.omega_pu[index + 1] - results.omega_pu[index - 1]
    ) / (
        results.time_s[index + 1] - results.time_s[index - 1]
    )
    expected_derivative = (
        results.mechanical_power_pu[index]
        - results.electrical_power_pu[index]
        - config.D * (results.omega_pu[index] - 1.0)
    ) / (2.0 * config.H)

    assert math.isclose(measured_derivative, expected_derivative, rel_tol=1e-3)
