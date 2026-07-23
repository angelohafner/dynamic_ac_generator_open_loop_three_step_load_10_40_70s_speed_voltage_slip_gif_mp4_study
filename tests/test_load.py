import math

import numpy as np

from dynamic_ac_generator import load as load_module
from dynamic_ac_generator.config import SimulationConfig


def test_impedance_load_returns_expected_magnitude_and_angle_before_and_after_steps() -> None:
    assert hasattr(load_module, "ImpedanceLoad")
    config = SimulationConfig()
    load = load_module.ImpedanceLoad(config)

    assert math.isclose(load.impedance_magnitude_pu_at(9.0), 0.5, rel_tol=1e-12)
    assert math.isclose(load.impedance_angle_deg_at(9.0), -45.0, rel_tol=1e-12)
    assert math.isclose(load.impedance_magnitude_pu_at(10.0), 0.6, rel_tol=1e-12)
    assert math.isclose(load.impedance_angle_deg_at(10.0), -30.0, rel_tol=1e-12)
    assert math.isclose(load.impedance_magnitude_pu_at(40.0), 0.6, rel_tol=1e-12)
    assert math.isclose(load.impedance_angle_deg_at(40.0), -60.0, rel_tol=1e-12)
    assert math.isclose(load.impedance_magnitude_pu_at(70.0), config.INITIAL_LOAD_PU, rel_tol=1e-12)
    assert math.isclose(load.impedance_angle_deg_at(70.0), config.INITIAL_LOAD_ANGLE_DEG, rel_tol=1e-12)


def test_impedance_load_supports_array_inputs() -> None:
    assert hasattr(load_module, "ImpedanceLoad")
    config = SimulationConfig()
    load = load_module.ImpedanceLoad(config)
    time_s = np.array([0.0, 9.0, 10.0, 11.0, 40.0, 41.0, 70.0, 71.0], dtype=float)

    impedance_pu = load.impedance_pu_at(time_s)
    impedance_ohm = load.impedance_at(time_s)
    magnitude_ohm = load.impedance_magnitude_ohm_at(time_s)
    angle_deg = load.impedance_angle_deg_at(time_s)

    assert np.allclose(
        np.abs(impedance_pu),
        np.array(
            [
                0.5,
                0.5,
                0.6,
                0.6,
                0.6,
                0.6,
                config.INITIAL_LOAD_PU,
                config.INITIAL_LOAD_PU,
            ],
            dtype=float,
        ),
    )
    assert np.allclose(
        angle_deg,
        np.array(
            [
                -45.0,
                -45.0,
                -30.0,
                -30.0,
                -60.0,
                -60.0,
                -45.0,
                -45.0,
            ],
            dtype=float,
        ),
    )
    assert np.allclose(magnitude_ohm, np.abs(impedance_pu) * config.impedance_base_ohm)
    assert np.allclose(impedance_ohm, impedance_pu * config.impedance_base_ohm)


def test_nominal_voltage_active_power_uses_complex_impedance_angle() -> None:
    assert hasattr(load_module, "ImpedanceLoad")
    config = SimulationConfig()
    load = load_module.ImpedanceLoad(config)

    assert math.isclose(load.nominal_voltage_active_power_pu_at(0.0), math.sqrt(2.0), rel_tol=1e-12)
    assert math.isclose(
        load.nominal_voltage_reactive_power_pu_at(0.0),
        -math.sqrt(2.0),
        rel_tol=1e-12,
    )
