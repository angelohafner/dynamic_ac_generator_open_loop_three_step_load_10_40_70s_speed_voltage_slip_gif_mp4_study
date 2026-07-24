import math

import numpy as np

from dynamic_ac_generator import load as load_module
from dynamic_ac_generator.config import SimulationConfig


def test_parallel_admittance_load_returns_expected_power_and_admittance_steps() -> None:
    assert hasattr(load_module, "ImpedanceLoad")
    config = SimulationConfig()
    load = load_module.ImpedanceLoad(config)

    assert config.LOAD_MODEL == "parallel_admittance"
    assert math.isclose(load.load_value_pu_at(9.0), 0.5, rel_tol=1e-12)
    assert math.isclose(load.load_angle_deg_at(9.0), -45.0, rel_tol=1e-12)
    assert math.isclose(load.load_value_pu_at(10.0), 1.0, rel_tol=1e-12)
    assert math.isclose(load.load_angle_deg_at(10.0), -30.0, rel_tol=1e-12)
    assert math.isclose(load.load_value_pu_at(40.0), 0.8, rel_tol=1e-12)
    assert math.isclose(load.load_angle_deg_at(40.0), -60.0, rel_tol=1e-12)
    assert math.isclose(load.load_value_pu_at(70.0), 0.8, rel_tol=1e-12)
    assert math.isclose(load.load_angle_deg_at(70.0), 60.0, rel_tol=1e-12)

    initial_admittance = load.admittance_pu_at(9.0)
    final_admittance = load.admittance_pu_at(70.0)
    assert math.isclose(initial_admittance.real, 0.5, rel_tol=1e-12)
    assert math.isclose(initial_admittance.imag, 0.5, rel_tol=1e-12)
    assert math.isclose(final_admittance.real, 0.8, rel_tol=1e-12)
    assert math.isclose(final_admittance.imag, -0.8 * math.tan(math.radians(60.0)), rel_tol=1e-12)
    assert load.susceptance_pu_at(9.0) > 0.0
    assert load.susceptance_pu_at(70.0) < 0.0


def test_parallel_admittance_load_supports_array_inputs_and_equivalent_impedance() -> None:
    assert hasattr(load_module, "ImpedanceLoad")
    config = SimulationConfig()
    load = load_module.ImpedanceLoad(config)
    time_s = np.array([0.0, 9.0, 10.0, 11.0, 40.0, 41.0, 70.0, 71.0], dtype=float)

    load_value_pu = load.load_value_pu_at(time_s)
    admittance_pu = load.admittance_pu_at(time_s)
    impedance_pu = load.impedance_pu_at(time_s)
    impedance_ohm = load.impedance_at(time_s)
    magnitude_ohm = load.impedance_magnitude_ohm_at(time_s)
    angle_deg = load.impedance_angle_deg_at(time_s)

    assert np.allclose(
        load_value_pu,
        np.array(
            [
                0.5,
                0.5,
                1.0,
                1.0,
                0.8,
                0.8,
                0.8,
                0.8,
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
                60.0,
                60.0,
            ],
            dtype=float,
        ),
    )
    assert np.allclose(impedance_pu, 1.0 / admittance_pu)
    assert np.allclose(magnitude_ohm, np.abs(impedance_pu) * config.impedance_base_ohm)
    assert np.allclose(impedance_ohm, impedance_pu * config.impedance_base_ohm)


def test_nominal_voltage_active_power_uses_complex_impedance_angle() -> None:
    assert hasattr(load_module, "ImpedanceLoad")
    config = SimulationConfig()
    load = load_module.ImpedanceLoad(config)

    assert math.isclose(load.nominal_voltage_active_power_pu_at(0.0), 0.5, rel_tol=1e-12)
    assert math.isclose(load.nominal_voltage_active_power_pu_at(10.0), 1.0, rel_tol=1e-12)
    assert math.isclose(load.nominal_voltage_active_power_pu_at(40.0), 0.8, rel_tol=1e-12)
    assert math.isclose(load.nominal_voltage_active_power_pu_at(70.0), 0.8, rel_tol=1e-12)
    assert math.isclose(
        load.nominal_voltage_reactive_power_pu_at(0.0),
        -0.5,
        rel_tol=1e-12,
    )


def test_series_impedance_load_mode_remains_available() -> None:
    config = SimulationConfig(
        LOAD_MODEL="series_impedance",
        INITIAL_LOAD_PU=math.sqrt(2.0),
        INITIAL_LOAD_ANGLE_DEG=-45.0,
        FINAL_LOAD_PU=0.8660254037844387,
        FINAL_LOAD_ANGLE_DEG=-30.0,
        SECOND_STEP_LOAD_PU=0.625,
        SECOND_STEP_LOAD_ANGLE_DEG=-60.0,
        THIRD_STEP_LOAD_PU=0.625,
        THIRD_STEP_LOAD_ANGLE_DEG=60.0,
    )
    load = load_module.ImpedanceLoad(config)

    assert math.isclose(load.impedance_magnitude_pu_at(9.0), math.sqrt(2.0), rel_tol=1e-12)
    assert math.isclose(load.impedance_angle_deg_at(9.0), -45.0, rel_tol=1e-12)
    assert math.isclose(load.nominal_voltage_active_power_pu_at(0.0), 0.5, rel_tol=1e-12)
    assert math.isclose(load.nominal_voltage_reactive_power_pu_at(0.0), -0.5, rel_tol=1e-12)
