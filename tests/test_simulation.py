import inspect
import math
import numpy as np
import pytest

import dynamic_ac_generator.runner as runner
from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.damping import calculate_unregulated_frequency_theory
from dynamic_ac_generator.runner import RunArtifacts, run_complete_simulation
from dynamic_ac_generator.results import SimulationResults
from dynamic_ac_generator.simulation import DynamicSimulation
from dynamic_ac_generator.validation import build_validation_report


@pytest.fixture(scope="module")
def default_results() -> SimulationResults:
    config = SimulationConfig()
    return DynamicSimulation(config).run()


@pytest.fixture(scope="module")
def pi_results() -> SimulationResults:
    config = SimulationConfig(
        CONTROL_MODE="pi",
        SIMULATION_TIME_S=24.0,
        SECOND_LOAD_STEP_TIME_S=None,
        SECOND_STEP_LOAD_PU=None,
        SECOND_STEP_LOAD_ANGLE_DEG=None,
        THIRD_LOAD_STEP_TIME_S=None,
        THIRD_STEP_LOAD_PU=None,
        THIRD_STEP_LOAD_ANGLE_DEG=None,
    )
    return DynamicSimulation(config).run()


@pytest.fixture(scope="module")
def default_artifacts(tmp_path_factory: pytest.TempPathFactory) -> RunArtifacts:
    output_dir = tmp_path_factory.mktemp("complete_unregulated_run")
    return run_complete_simulation(output_dir=output_dir, save_animations=False)


def test_simulation_starts_in_steady_state(default_results: SimulationResults) -> None:
    results = default_results

    assert math.isclose(results.frequency_hz[0], 60.0, abs_tol=1e-9)
    assert math.isclose(results.mechanical_power_pu[0], results.electrical_power_pu[0], abs_tol=1e-9)


def test_unregulated_generator_keeps_mechanical_power_constant_after_load_step(default_results: SimulationResults) -> None:
    results = default_results
    config = results.config
    step_index = int(np.searchsorted(results.time_s, config.LOAD_STEP_TIME_S))
    later_index = int(np.searchsorted(results.time_s, config.LOAD_STEP_TIME_S + 0.20))
    second_step_index = int(np.searchsorted(results.time_s, config.SECOND_LOAD_STEP_TIME_S))
    after_second_step_index = int(np.searchsorted(results.time_s, config.SECOND_LOAD_STEP_TIME_S + 0.20))
    second_step_sign_index = int(np.searchsorted(results.time_s, config.SECOND_LOAD_STEP_TIME_S + 0.02))
    second_step_frequency_change_hz = float(
        results.frequency_hz[after_second_step_index] - results.frequency_hz[second_step_index]
    )
    second_step_power_imbalance_pu = float(
        results.mechanical_power_pu[second_step_sign_index]
        - results.electrical_power_pu[second_step_sign_index]
    )

    assert results.frequency_hz[later_index] < results.frequency_hz[step_index] - 0.01
    assert abs(second_step_frequency_change_hz) > 0.01
    assert second_step_frequency_change_hz * second_step_power_imbalance_pu > 0.0
    assert math.isclose(results.mechanical_power_pu[-1], config.initial_active_power_pu, abs_tol=1e-9)
    assert math.isclose(results.mechanical_power_reference_pu[-1], config.initial_active_power_pu, abs_tol=1e-9)
    assert math.isclose(results.electrical_power_pu[-1], results.mechanical_power_pu[-1], abs_tol=0.05)


def test_unregulated_speed_coupled_voltage_generator_moves_toward_low_frequency_equilibrium_after_inductive_step(
    default_results: SimulationResults,
) -> None:
    results = default_results
    config = results.config
    theory = calculate_unregulated_frequency_theory(config)
    third_step_index = int(np.searchsorted(results.time_s, config.THIRD_LOAD_STEP_TIME_S))
    after_third_step_index = int(np.searchsorted(results.time_s, config.THIRD_LOAD_STEP_TIME_S + 0.20))

    assert theory.has_finite_equilibrium
    assert results.frequency_hz.min() < config.F_NOM_HZ - 15.0
    assert results.frequency_hz[after_third_step_index] > results.frequency_hz[third_step_index] + 0.01
    assert math.isclose(theory.final_frequency_hz, 58.2944625735, abs_tol=1e-6)
    assert results.frequency_hz[-1] < config.F_NOM_HZ
    assert math.isclose(
        results.frequency_hz[-1],
        theory.final_frequency_hz,
        abs_tol=5.0 * config.DAMPING_SETTLING_TOLERANCE_HZ,
    )


def test_pi_governor_returns_close_to_nominal_frequency(pi_results: SimulationResults) -> None:
    results = pi_results
    config = results.config

    assert abs(results.frequency_hz[-1] - config.F_NOM_HZ) <= 0.10


def test_validation_report_passes_for_unregulated_default_case(default_results: SimulationResults) -> None:
    results = default_results
    config = results.config
    simulation = DynamicSimulation(config)
    waveform_window = simulation.waveform_dataframe(
        results,
        config.LOAD_STEP_TIME_S,
        config.LOAD_STEP_TIME_S + config.WAVEFORM_WINDOW_S,
    )

    report = build_validation_report(results, waveform_window)

    assert set(report["status"]) <= {"PASS", "WARNING"}
    assert "FAIL" not in set(report["status"])
    assert "Frequency initially follows the first load-change power imbalance" in set(report["check"])
    assert "Terminal voltage changes after the first load change" in set(report["check"])
    assert "Frequency follows the second load-change power imbalance" in set(report["check"])
    assert "Frequency follows the third load-change power imbalance" in set(report["check"])


def test_validation_report_passes_for_pi_case(pi_results: SimulationResults) -> None:
    results = pi_results
    config = results.config
    simulation = DynamicSimulation(config)
    waveform_window = simulation.waveform_dataframe(
        results,
        config.LOAD_STEP_TIME_S,
        config.LOAD_STEP_TIME_S + config.WAVEFORM_WINDOW_S,
    )

    report = build_validation_report(results, waveform_window)

    assert set(report["status"]) == {"PASS"}


def test_complete_run_uses_unregulated_default_case_and_can_skip_animations(default_artifacts: RunArtifacts) -> None:
    artifacts = default_artifacts
    assert not hasattr(artifacts, "proportional_results")
    assert not hasattr(artifacts, "comparison_table")
    assert not (artifacts.output_dir / "governor_comparison.csv").exists()
    assert artifacts.animation_paths == []
    assert artifacts.results.config.CONTROL_MODE == "unregulated"
    theory = calculate_unregulated_frequency_theory(artifacts.results.config)
    assert math.isclose(theory.final_frequency_hz, 58.2944625735, abs_tol=1e-6)
    assert math.isclose(
        artifacts.results.frequency_hz[-1],
        theory.final_frequency_hz,
        abs_tol=5.0 * artifacts.results.config.DAMPING_SETTLING_TOLERANCE_HZ,
    )


def test_complete_run_does_not_append_damping_gif_animation() -> None:
    source = inspect.getsource(runner.run_complete_simulation)

    assert "generate_all_animations" in source
    assert "generate_damping_comparison_animation" not in source


def test_default_unregulated_figures_do_not_use_governor_file_names(default_artifacts: RunArtifacts) -> None:
    artifacts = default_artifacts
    figure_names = [figure_path.name for figure_path in artifacts.figure_paths]

    assert "06_constant_mechanical_input.png" in figure_names
    assert all("governor" not in figure_name for figure_name in figure_names)
