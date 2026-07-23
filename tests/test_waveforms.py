import math

import numpy as np

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.generator import GeneratorModel
from dynamic_ac_generator.governor import IsochronousGovernor
from dynamic_ac_generator.load import ImpedanceLoad
from dynamic_ac_generator.simulation import DynamicSimulation
from dynamic_ac_generator.validation import estimate_phase_displacement_degrees


def test_three_phase_voltages_are_displaced_by_about_120_degrees() -> None:
    config = SimulationConfig()
    load = ImpedanceLoad(config)
    governor = IsochronousGovernor(config)
    model = GeneratorModel(config, load, governor)
    theta_rad = np.linspace(0.0, 2.0 * math.pi, 10_000, endpoint=False)

    voltage_a_v, voltage_b_v, voltage_c_v = model.three_phase_voltages(theta_rad)

    assert abs(estimate_phase_displacement_degrees(voltage_a_v, voltage_b_v) - 120.0) <= 1.0
    assert abs(estimate_phase_displacement_degrees(voltage_a_v, voltage_c_v) - 120.0) <= 1.0


def test_balanced_impedance_load_has_smooth_total_instantaneous_power() -> None:
    config = SimulationConfig()
    simulation = DynamicSimulation(config)
    results = simulation.run()
    waveform = simulation.waveform_dataframe(
        results,
        config.LOAD_STEP_TIME_S,
        config.LOAD_STEP_TIME_S + config.WAVEFORM_WINDOW_S,
    )

    relative_std = waveform["total_power_w"].std() / abs(waveform["total_power_w"].mean())

    assert relative_std <= 1e-2
