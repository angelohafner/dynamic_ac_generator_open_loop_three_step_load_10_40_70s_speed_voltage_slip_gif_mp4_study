import math

import numpy as np

from dynamic_ac_generator import load as load_module
from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.damping import calculate_unregulated_frequency_theory
from dynamic_ac_generator.electrical import TerminalElectricalModel
from dynamic_ac_generator.excitation import OpenLoopExcitationModel
from dynamic_ac_generator.runner import run_complete_simulation
from dynamic_ac_generator.simulation import DynamicSimulation


def test_excitation_initial_current_produces_nominal_terminal_voltage() -> None:
    config = SimulationConfig()
    excitation = OpenLoopExcitationModel(config)
    electrical = TerminalElectricalModel(config, excitation)

    terminal = electrical.solve_terminal_quantities(
        config.initial_impedance_ohm,
        config.FIELD_CURRENT_INITIAL_PU,
        omega_pu=1.0,
    )
    assert hasattr(load_module, "ImpedanceLoad")
    load = load_module.ImpedanceLoad(config)

    assert math.isclose(terminal.terminal_voltage_ll_rms, config.V_LL_RMS, rel_tol=1e-12)
    assert terminal.internal_voltage_ll_rms > 0.0
    assert math.isclose(terminal.electrical_power_pu, load.nominal_voltage_active_power_pu_at(0.0), rel_tol=1e-12)
    assert math.isclose(terminal.reactive_power_pu, load.nominal_voltage_reactive_power_pu_at(0.0), rel_tol=1e-12)
    assert terminal.load_current_angle_rad > terminal.terminal_voltage_angle_rad


def test_excitation_voltage_is_proportional_to_field_current_and_speed() -> None:
    config = SimulationConfig()
    excitation = OpenLoopExcitationModel(config)

    nominal_voltage = excitation.internal_voltage_ll_rms(config.FIELD_CURRENT_INITIAL_PU, omega_pu=1.0)
    slow_voltage = excitation.internal_voltage_ll_rms(config.FIELD_CURRENT_INITIAL_PU, omega_pu=0.8)

    assert math.isclose(slow_voltage, 0.8 * nominal_voltage, rel_tol=1e-12)


def test_open_loop_load_step_changes_voltage_with_constant_field_current() -> None:
    config = SimulationConfig()
    results = DynamicSimulation(config).run()

    step_index = int(np.searchsorted(results.time_s, config.LOAD_STEP_TIME_S))

    assert math.isclose(results.field_current_pu[0], config.FIELD_CURRENT_INITIAL_PU, abs_tol=1e-12)
    assert math.isclose(results.field_current_pu[-1], config.FIELD_CURRENT_INITIAL_PU, abs_tol=1e-12)
    assert math.isclose(results.terminal_voltage_ll_rms[0], config.V_LL_RMS, abs_tol=1e-9)
    assert results.terminal_voltage_ll_rms[step_index + 1] < results.terminal_voltage_ll_rms[0]
    assert math.isclose(
        results.internal_voltage_ll_rms[step_index + 1] / results.internal_voltage_ll_rms[0],
        results.omega_pu[step_index + 1],
        rel_tol=1e-9,
    )
    assert results.internal_voltage_ll_rms[-1] > results.internal_voltage_ll_rms[0]
    assert math.isclose(
        results.internal_voltage_ll_rms[-1] / results.internal_voltage_ll_rms[0],
        results.omega_pu[-1],
        rel_tol=1e-9,
    )
    theory = calculate_unregulated_frequency_theory(config)
    assert results.frequency_hz[-1] > config.F_NOM_HZ + 10.0
    assert math.isclose(
        results.frequency_hz[-1],
        theory.final_frequency_hz,
        abs_tol=config.DAMPING_SETTLING_TOLERANCE_HZ,
    )
    assert results.electrical_power_pu[step_index + 1] > results.electrical_power_pu[0]
    assert results.reactive_power_pu[step_index + 1] < 0.0


def test_waveform_dataframe_uses_terminal_voltage_after_load_step() -> None:
    config = SimulationConfig()
    simulation = DynamicSimulation(config)
    results = simulation.run()
    waveform = simulation.waveform_dataframe(
        results,
        config.LOAD_STEP_TIME_S,
        config.LOAD_STEP_TIME_S + config.WAVEFORM_WINDOW_S,
    )

    terminal_voltage_phase_peak = (
        results.terminal_voltage_ll_rms[
            int(np.searchsorted(results.time_s, config.LOAD_STEP_TIME_S + 0.01))
        ]
        / math.sqrt(3.0)
        * math.sqrt(2.0)
    )

    assert waveform["voltage_a_v"].abs().max() <= terminal_voltage_phase_peak * 1.02
    assert waveform["field_current_pu"].nunique() == 1


def test_complete_run_writes_open_loop_voltage_outputs(tmp_path) -> None:
    artifacts = run_complete_simulation(output_dir=tmp_path, save_animations=False)

    figure_names = [figure_path.name for figure_path in artifacts.figure_paths]

    assert "17_open_loop_internal_terminal_voltage.png" in figure_names
    assert "18_open_loop_load_current_field_current.png" in figure_names
    assert "19_open_loop_power_speed_equilibrium.png" in figure_names
    assert "field_current_pu" in artifacts.results.to_dataframe().columns
    assert "terminal_voltage_ll_rms" in artifacts.results.to_dataframe().columns
    assert "load_impedance_magnitude_ohm" in artifacts.results.to_dataframe().columns
    assert "load_impedance_angle_deg" in artifacts.results.to_dataframe().columns
    assert "load_admittance_real_pu" in artifacts.results.to_dataframe().columns
    assert "load_admittance_imag_pu" in artifacts.results.to_dataframe().columns
    assert "load_admittance_magnitude_pu" in artifacts.results.to_dataframe().columns
    assert "load_admittance_angle_deg" in artifacts.results.to_dataframe().columns
    assert "load_conductance_pu" in artifacts.results.to_dataframe().columns
    assert "load_susceptance_pu" in artifacts.results.to_dataframe().columns
    assert "reactive_power_pu" in artifacts.results.to_dataframe().columns
    assert artifacts.open_loop_equilibrium_curve_path is not None
    assert artifacts.open_loop_equilibrium_curve_path.exists()
