import math

import numpy as np

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.load import ResistiveLoad


def test_resistive_load_returns_expected_power_before_and_after_step() -> None:
    config = SimulationConfig()
    load = ResistiveLoad(config)

    assert math.isclose(load.electrical_power_pu_at(9.0), 0.5, rel_tol=1e-12)
    assert math.isclose(load.electrical_power_pu_at(10.0), 0.8, rel_tol=1e-12)
    assert math.isclose(load.electrical_power_pu_at(40.0), 0.2, rel_tol=1e-12)
    assert math.isclose(load.electrical_power_pu_at(70.0), config.INITIAL_LOAD_PU, rel_tol=1e-12)


def test_resistive_load_supports_array_inputs() -> None:
    config = SimulationConfig()
    load = ResistiveLoad(config)
    time_s = np.array([0.0, 9.0, 10.0, 11.0, 40.0, 41.0, 70.0, 71.0], dtype=float)

    power_pu = load.electrical_power_pu_at(time_s)
    resistance_ohm = load.resistance_at(time_s)

    assert np.allclose(
        power_pu,
        np.array(
            [
                0.5,
                0.5,
                0.8,
                0.8,
                0.2,
                0.2,
                config.INITIAL_LOAD_PU,
                config.INITIAL_LOAD_PU,
            ],
            dtype=float,
        ),
    )
    assert np.allclose(
        resistance_ohm,
        np.array(
            [
                3.2,
                3.2,
                2.0,
                2.0,
                8.0,
                8.0,
                config.initial_resistance_ohm,
                config.initial_resistance_ohm,
            ],
            dtype=float,
        ),
    )
