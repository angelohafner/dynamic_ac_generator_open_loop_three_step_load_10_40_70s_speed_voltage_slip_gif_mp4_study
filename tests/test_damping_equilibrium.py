import math

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.damping import build_damping_comparison, calculate_unregulated_frequency_theory
from dynamic_ac_generator.results import calculate_settling_time
from dynamic_ac_generator.runner import run_complete_simulation
from dynamic_ac_generator.simulation import DynamicSimulation


def test_undamped_speed_coupled_voltage_case_has_higher_frequency_equilibrium() -> None:
    config = SimulationConfig(CONTROL_MODE="unregulated", D=0.0, ADDITIONAL_LOAD_STEPS=())

    theory = calculate_unregulated_frequency_theory(config)

    assert theory.has_finite_equilibrium
    assert theory.final_frequency_hz > config.F_NOM_HZ
    assert math.isclose(
        theory.electrical_power_pu,
        theory.mechanical_power_pu,
        abs_tol=1e-12,
    )


def test_damped_unregulated_theory_predicts_lower_stable_frequency() -> None:
    config = SimulationConfig(CONTROL_MODE="unregulated", D=2.0, ADDITIONAL_LOAD_STEPS=())

    theory = calculate_unregulated_frequency_theory(config)
    expected_final_frequency_hz = config.F_NOM_HZ * (
        1.0 + (theory.mechanical_power_pu - theory.electrical_power_pu) / config.D
    )

    assert theory.has_finite_equilibrium
    assert math.isclose(theory.final_frequency_hz, expected_final_frequency_hz, abs_tol=1e-9)
    assert theory.final_frequency_hz > config.F_NOM_HZ
    assert 0.0 < theory.time_constant_s < 3.0
    assert theory.settling_time_s > config.LOAD_STEP_TIME_S
    assert theory.settling_time_after_step_s < 5.0


def test_damped_unregulated_simulation_converges_to_theoretical_frequency() -> None:
    config = SimulationConfig(
        CONTROL_MODE="unregulated",
        D=2.0,
        SIMULATION_TIME_S=24.0,
        ADDITIONAL_LOAD_STEPS=(),
    )
    results = DynamicSimulation(config).run()
    theory = calculate_unregulated_frequency_theory(config)

    assert theory.has_finite_equilibrium
    assert math.isclose(results.frequency_hz[-1], theory.final_frequency_hz, abs_tol=0.05)
    assert math.isclose(results.mechanical_power_pu[-1], config.initial_active_power_pu, abs_tol=1e-9)


def test_undamped_speed_coupled_voltage_simulation_converges_to_theoretical_frequency() -> None:
    config = SimulationConfig(
        CONTROL_MODE="unregulated",
        D=0.0,
        SIMULATION_TIME_S=100.0,
        DYNAMIC_SAMPLE_STEP_S=0.01,
        THIRD_LOAD_STEP_TIME_S=None,
        THIRD_STEP_LOAD_PU=None,
    )

    results = DynamicSimulation(config).run()
    theory = calculate_unregulated_frequency_theory(config)

    assert theory.has_finite_equilibrium
    assert math.isclose(
        results.frequency_hz[-1],
        theory.final_frequency_hz,
        abs_tol=config.DAMPING_SETTLING_TOLERANCE_HZ,
    )
    assert math.isclose(results.electrical_power_pu[-1], results.mechanical_power_pu[-1], abs_tol=0.01)


def test_default_speed_coupled_case_reports_finite_settling_time() -> None:
    config = SimulationConfig(CONTROL_MODE="unregulated", D=0.0)
    results = DynamicSimulation(config).run()

    settling_time_s = calculate_settling_time(results)

    assert settling_time_s > config.LOAD_STEP_TIME_S
    assert settling_time_s < config.SIMULATION_TIME_S


def test_default_three_step_case_predicts_return_to_60_hz_equilibrium() -> None:
    config = SimulationConfig(CONTROL_MODE="unregulated", D=0.0)

    theory = calculate_unregulated_frequency_theory(config)

    assert theory.has_finite_equilibrium
    assert math.isclose(theory.final_frequency_hz, config.F_NOM_HZ, abs_tol=0.01)
    assert theory.settling_time_s > config.THIRD_LOAD_STEP_TIME_S
    assert theory.settling_time_s < config.SIMULATION_TIME_S


def test_damping_comparison_contains_undamped_and_damped_frequency_columns() -> None:
    base_config = SimulationConfig(CONTROL_MODE="unregulated")

    comparison = build_damping_comparison(base_config)

    assert comparison.theory.has_finite_equilibrium
    assert comparison.table["frequency_no_damping_hz"].iloc[-1] > base_config.F_NOM_HZ - 0.50
    assert math.isclose(
        comparison.table["frequency_with_damping_hz"].iloc[-1],
        comparison.theory.final_frequency_hz,
        abs_tol=0.50,
    )


def test_complete_run_writes_damping_comparison_outputs_for_default_case(tmp_path) -> None:
    artifacts = run_complete_simulation(output_dir=tmp_path, save_animations=False)

    assert artifacts.damping_theory_path is not None
    assert artifacts.damping_comparison_path is not None
    assert artifacts.damping_theory_path.exists()
    assert artifacts.damping_comparison_path.exists()
    assert (tmp_path / "figures" / "15_unregulated_damping_frequency_comparison.png").exists()
    assert (tmp_path / "figures" / "16_unregulated_damping_power_imbalance_comparison.png").exists()
