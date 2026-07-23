import math
import numpy as np

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.damping import calculate_unregulated_frequency_theory
from dynamic_ac_generator.runner import run_complete_simulation
from dynamic_ac_generator.simulation import DynamicSimulation
from dynamic_ac_generator.validation import build_validation_report


def test_simulation_starts_in_steady_state() -> None:
    config = SimulationConfig()
    results = DynamicSimulation(config).run()

    assert math.isclose(results.frequency_hz[0], 60.0, abs_tol=1e-9)
    assert math.isclose(results.mechanical_power_pu[0], results.electrical_power_pu[0], abs_tol=1e-9)


def test_unregulated_generator_keeps_mechanical_power_constant_after_load_step() -> None:
    config = SimulationConfig()
    results = DynamicSimulation(config).run()
    step_index = int(np.searchsorted(results.time_s, config.LOAD_STEP_TIME_S))
    later_index = int(np.searchsorted(results.time_s, config.LOAD_STEP_TIME_S + 0.20))
    second_step_index = int(np.searchsorted(results.time_s, config.SECOND_LOAD_STEP_TIME_S))
    after_second_step_index = int(np.searchsorted(results.time_s, config.SECOND_LOAD_STEP_TIME_S + 0.20))

    assert results.frequency_hz[later_index] > results.frequency_hz[step_index] + 0.01
    assert results.frequency_hz[after_second_step_index] < results.frequency_hz[second_step_index] - 0.01
    assert math.isclose(results.mechanical_power_pu[-1], config.initial_active_power_pu, abs_tol=1e-9)
    assert math.isclose(results.mechanical_power_reference_pu[-1], config.initial_active_power_pu, abs_tol=1e-9)
    assert math.isclose(results.electrical_power_pu[-1], results.mechanical_power_pu[-1], abs_tol=0.01)


def test_unregulated_speed_coupled_voltage_generator_returns_to_60_hz_after_restored_impedance() -> None:
    config = SimulationConfig()
    results = DynamicSimulation(config).run()
    theory = calculate_unregulated_frequency_theory(config)
    third_step_index = int(np.searchsorted(results.time_s, config.THIRD_LOAD_STEP_TIME_S))
    after_third_step_index = int(np.searchsorted(results.time_s, config.THIRD_LOAD_STEP_TIME_S + 0.20))

    assert theory.has_finite_equilibrium
    assert results.frequency_hz.max() > config.F_NOM_HZ + 5.0
    assert results.frequency_hz[after_third_step_index] > results.frequency_hz[third_step_index] + 0.01
    assert math.isclose(theory.final_frequency_hz, config.F_NOM_HZ, abs_tol=0.01)
    assert math.isclose(
        results.frequency_hz[-1],
        theory.final_frequency_hz,
        abs_tol=config.DAMPING_SETTLING_TOLERANCE_HZ,
    )


def test_pi_governor_returns_close_to_nominal_frequency() -> None:
    config = SimulationConfig(CONTROL_MODE="pi")
    results = DynamicSimulation(config).run()

    assert abs(results.frequency_hz[-1] - config.F_NOM_HZ) <= 0.10


def test_validation_report_passes_for_unregulated_default_case() -> None:
    config = SimulationConfig()
    simulation = DynamicSimulation(config)
    results = simulation.run()
    waveform_window = simulation.waveform_dataframe(
        results,
        config.LOAD_STEP_TIME_S,
        config.LOAD_STEP_TIME_S + config.WAVEFORM_WINDOW_S,
    )

    report = build_validation_report(results, waveform_window)

    assert set(report["status"]) == {"PASS"}
    assert "Frequency decreases after the second impedance change" in set(report["check"])
    assert "Frequency increases after the third load restoration" in set(report["check"])


def test_validation_report_passes_for_pi_case() -> None:
    config = SimulationConfig(CONTROL_MODE="pi")
    simulation = DynamicSimulation(config)
    results = simulation.run()
    waveform_window = simulation.waveform_dataframe(
        results,
        config.LOAD_STEP_TIME_S,
        config.LOAD_STEP_TIME_S + config.WAVEFORM_WINDOW_S,
    )

    report = build_validation_report(results, waveform_window)

    assert set(report["status"]) == {"PASS"}


def test_complete_run_uses_unregulated_default_case_and_can_skip_animations(tmp_path) -> None:
    artifacts = run_complete_simulation(output_dir=tmp_path, save_animations=False)

    assert not hasattr(artifacts, "proportional_results")
    assert not hasattr(artifacts, "comparison_table")
    assert not (tmp_path / "governor_comparison.csv").exists()
    assert artifacts.animation_paths == []
    assert artifacts.results.config.CONTROL_MODE == "unregulated"
    theory = calculate_unregulated_frequency_theory(artifacts.results.config)
    assert math.isclose(theory.final_frequency_hz, artifacts.results.config.F_NOM_HZ, abs_tol=0.01)
    assert math.isclose(
        artifacts.results.frequency_hz[-1],
        theory.final_frequency_hz,
        abs_tol=artifacts.results.config.DAMPING_SETTLING_TOLERANCE_HZ,
    )


def test_default_unregulated_figures_do_not_use_governor_file_names(tmp_path) -> None:
    artifacts = run_complete_simulation(output_dir=tmp_path, save_animations=False)

    figure_names = [figure_path.name for figure_path in artifacts.figure_paths]

    assert "06_constant_mechanical_input.png" in figure_names
    assert all("governor" not in figure_name for figure_name in figure_names)
