"""Damping theory and comparison helpers for the unregulated generator case."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
import math
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.electrical import TerminalElectricalModel
from dynamic_ac_generator.excitation import OpenLoopExcitationModel

if TYPE_CHECKING:
    from dynamic_ac_generator.results import SimulationResults


@dataclass(frozen=True)
class UnregulatedFrequencyTheory:
    """Theoretical frequency equilibrium for an unregulated damped generator."""

    damping_d: float
    mechanical_power_pu: float
    electrical_power_pu: float
    power_imbalance_pu: float
    has_finite_equilibrium: bool
    final_omega_pu: float
    final_frequency_hz: float
    time_constant_s: float
    settling_tolerance_hz: float
    settling_time_after_step_s: float
    settling_time_s: float
    two_percent_settling_time_s: float

    def to_dataframe(self, scenario: str) -> pd.DataFrame:
        """Return a one-row table with the theoretical quantities."""
        return pd.DataFrame(
            [
                {
                    "scenario": scenario,
                    "damping_D_pu": self.damping_d,
                    "mechanical_power_pu": self.mechanical_power_pu,
                    "electrical_power_pu": self.electrical_power_pu,
                    "power_imbalance_pu": self.power_imbalance_pu,
                    "has_finite_equilibrium": self.has_finite_equilibrium,
                    "final_omega_pu": self.final_omega_pu,
                    "final_frequency_hz": self.final_frequency_hz,
                    "time_constant_s": self.time_constant_s,
                    "settling_tolerance_hz": self.settling_tolerance_hz,
                    "settling_time_after_step_s": self.settling_time_after_step_s,
                    "settling_time_s": self.settling_time_s,
                    "two_percent_settling_time_s": self.two_percent_settling_time_s,
                }
            ]
        )


@dataclass(frozen=True)
class DampingComparison:
    """Simulation outputs used to compare undamped and damped unregulated cases."""

    undamped_results: "SimulationResults"
    damped_results: "SimulationResults"
    theory: UnregulatedFrequencyTheory
    table: pd.DataFrame


def calculate_unregulated_frequency_theory(config: SimulationConfig) -> UnregulatedFrequencyTheory:
    """Calculate the final equilibrium created by speed-coupled voltage."""
    electrical_model = TerminalElectricalModel(config, OpenLoopExcitationModel(config))
    initial_terminal = electrical_model.solve_terminal_quantities(
        config.initial_resistance_ohm,
        config.FIELD_CURRENT_INITIAL_PU,
        omega_pu=1.0,
    )
    final_terminal_at_nominal_speed = electrical_model.solve_terminal_quantities(
        config.final_resistance_ohm,
        config.FIELD_CURRENT_INITIAL_PU,
        omega_pu=1.0,
    )
    mechanical_power_pu = initial_terminal.electrical_power_pu
    final_load_power_coefficient_pu = final_terminal_at_nominal_speed.electrical_power_pu

    def equilibrium_omega_pu(load_power_coefficient_pu: float) -> float:
        """Return equilibrium speed for a load coefficient at nominal speed."""
        if config.D == 0.0:
            return math.sqrt(mechanical_power_pu / load_power_coefficient_pu)
        discriminant = config.D**2 + 4.0 * load_power_coefficient_pu * (
            mechanical_power_pu + config.D
        )
        return (-config.D + math.sqrt(discriminant)) / (
            2.0 * load_power_coefficient_pu
        )

    if final_load_power_coefficient_pu <= 0.0:
        return UnregulatedFrequencyTheory(
            damping_d=config.D,
            mechanical_power_pu=mechanical_power_pu,
            electrical_power_pu=math.nan,
            power_imbalance_pu=math.nan,
            has_finite_equilibrium=False,
            final_omega_pu=math.nan,
            final_frequency_hz=math.nan,
            time_constant_s=math.nan,
            settling_tolerance_hz=config.DAMPING_SETTLING_TOLERANCE_HZ,
            settling_time_after_step_s=math.nan,
            settling_time_s=math.nan,
            two_percent_settling_time_s=math.nan,
        )

    final_omega_pu = equilibrium_omega_pu(final_load_power_coefficient_pu)

    electrical_power_pu = final_load_power_coefficient_pu * final_omega_pu**2
    power_imbalance_pu = mechanical_power_pu - electrical_power_pu
    final_frequency_hz = config.F_NOM_HZ * final_omega_pu
    linearized_restoring_gain = 2.0 * final_load_power_coefficient_pu * final_omega_pu + config.D
    time_constant_s = 2.0 * config.H / linearized_restoring_gain
    previous_load_power_pu = config.load_schedule[-2][1]
    previous_resistance_ohm = config.resistance_for_load_power_pu(previous_load_power_pu)
    previous_terminal_at_nominal_speed = electrical_model.solve_terminal_quantities(
        previous_resistance_ohm,
        config.FIELD_CURRENT_INITIAL_PU,
        omega_pu=1.0,
    )
    previous_omega_pu = equilibrium_omega_pu(previous_terminal_at_nominal_speed.electrical_power_pu)
    previous_frequency_hz = config.F_NOM_HZ * previous_omega_pu
    initial_frequency_distance_hz = abs(previous_frequency_hz - final_frequency_hz)
    if final_omega_pu <= 0.0:
        has_finite_equilibrium = False
        settling_time_after_step_s = math.nan
        settling_time_s = math.nan
        two_percent_settling_time_s = math.nan
    else:
        has_finite_equilibrium = True
        if initial_frequency_distance_hz <= config.DAMPING_SETTLING_TOLERANCE_HZ:
            settling_time_after_step_s = 0.0
        else:
            settling_time_after_step_s = time_constant_s * math.log(
                initial_frequency_distance_hz / config.DAMPING_SETTLING_TOLERANCE_HZ
            )
        settling_time_s = config.final_load_step_time_s + settling_time_after_step_s
        two_percent_settling_time_s = config.final_load_step_time_s + 4.0 * time_constant_s

    return UnregulatedFrequencyTheory(
        damping_d=config.D,
        mechanical_power_pu=mechanical_power_pu,
        electrical_power_pu=electrical_power_pu,
        power_imbalance_pu=power_imbalance_pu,
        has_finite_equilibrium=has_finite_equilibrium,
        final_omega_pu=final_omega_pu,
        final_frequency_hz=final_frequency_hz,
        time_constant_s=time_constant_s,
        settling_tolerance_hz=config.DAMPING_SETTLING_TOLERANCE_HZ,
        settling_time_after_step_s=settling_time_after_step_s,
        settling_time_s=settling_time_s,
        two_percent_settling_time_s=two_percent_settling_time_s,
    )


def build_damping_theory_table(
    selected_config: SimulationConfig,
    damped_config: SimulationConfig,
) -> pd.DataFrame:
    """Build a theory table for the selected and damped-comparison cases."""
    selected_theory = calculate_unregulated_frequency_theory(selected_config)
    damped_theory = calculate_unregulated_frequency_theory(damped_config)
    return pd.concat(
        [
            selected_theory.to_dataframe("selected_case"),
            damped_theory.to_dataframe("damped_comparison"),
        ],
        ignore_index=True,
    )


def build_open_loop_equilibrium_curve(
    config: SimulationConfig,
    point_count: int = 240,
) -> pd.DataFrame:
    """Build Pe versus omega data for old and speed-coupled voltage assumptions."""
    electrical_model = TerminalElectricalModel(config, OpenLoopExcitationModel(config))
    theory = calculate_unregulated_frequency_theory(config)
    upper_omega_pu = max(1.25, theory.final_omega_pu * 1.08 if theory.has_finite_equilibrium else 1.25)
    omega_pu = np.linspace(0.40, upper_omega_pu, point_count, dtype=float)
    field_current_pu = np.full_like(omega_pu, config.FIELD_CURRENT_INITIAL_PU, dtype=float)
    final_resistance_ohm = np.full_like(omega_pu, config.final_resistance_ohm, dtype=float)
    speed_coupled_quantities = electrical_model.terminal_quantities_at(
        final_resistance_ohm,
        field_current_pu,
        omega_pu,
    )
    old_constant_quantities = electrical_model.terminal_quantities_at(
        final_resistance_ohm,
        field_current_pu,
        np.ones_like(omega_pu, dtype=float),
    )
    return pd.DataFrame(
        {
            "omega_pu": omega_pu,
            "frequency_hz": config.F_NOM_HZ * omega_pu,
            "mechanical_power_pu": np.full_like(omega_pu, theory.mechanical_power_pu),
            "electrical_power_speed_coupled_pu": speed_coupled_quantities["electrical_power_pu"],
            "electrical_power_if_only_pu": old_constant_quantities["electrical_power_pu"],
            "terminal_voltage_speed_coupled_ll_rms": speed_coupled_quantities["terminal_voltage_ll_rms"],
            "terminal_voltage_if_only_ll_rms": old_constant_quantities["terminal_voltage_ll_rms"],
            "equilibrium_omega_pu": np.full_like(omega_pu, theory.final_omega_pu),
            "equilibrium_frequency_hz": np.full_like(omega_pu, theory.final_frequency_hz),
        }
    )


def build_damping_comparison(config: SimulationConfig) -> DampingComparison:
    """Run D=0 and D>0 unregulated simulations on a shared comparison horizon."""
    from dynamic_ac_generator.simulation import DynamicSimulation

    comparison_time_s = config.DAMPING_COMPARISON_SIMULATION_TIME_S
    undamped_config = replace(
        config,
        CONTROL_MODE="unregulated",
        D=0.0,
        SIMULATION_TIME_S=comparison_time_s,
    )
    damped_config = replace(
        config,
        CONTROL_MODE="unregulated",
        D=config.DAMPED_COMPARISON_D,
        SIMULATION_TIME_S=comparison_time_s,
    )
    undamped_results = DynamicSimulation(undamped_config).run()
    damped_results = DynamicSimulation(damped_config).run()
    theory = calculate_unregulated_frequency_theory(damped_config)

    time_s = damped_results.time_s
    no_damping_frequency_hz = np.interp(
        time_s,
        undamped_results.time_s,
        undamped_results.frequency_hz,
    )
    no_damping_omega_pu = no_damping_frequency_hz / config.F_NOM_HZ
    no_damping_power_imbalance_pu = np.interp(
        time_s,
        undamped_results.time_s,
        undamped_results.mechanical_power_pu - undamped_results.electrical_power_pu,
    )
    with_damping_power_imbalance_pu = damped_results.mechanical_power_pu - damped_results.electrical_power_pu
    damping_power_pu = damped_config.D * (damped_results.omega_pu - 1.0)
    accelerating_power_with_damping_pu = with_damping_power_imbalance_pu - damping_power_pu

    table = pd.DataFrame(
        {
            "time_s": time_s,
            "frequency_no_damping_hz": no_damping_frequency_hz,
            "frequency_with_damping_hz": damped_results.frequency_hz,
            "omega_no_damping_pu": no_damping_omega_pu,
            "omega_with_damping_pu": damped_results.omega_pu,
            "mechanical_power_pu": damped_results.mechanical_power_pu,
            "electrical_power_pu": damped_results.electrical_power_pu,
            "power_imbalance_no_damping_pu": no_damping_power_imbalance_pu,
            "power_imbalance_with_damping_pu": with_damping_power_imbalance_pu,
            "damping_power_pu": damping_power_pu,
            "accelerating_power_no_damping_pu": no_damping_power_imbalance_pu,
            "accelerating_power_with_damping_pu": accelerating_power_with_damping_pu,
            "expected_final_frequency_with_damping_hz": theory.final_frequency_hz,
        }
    )

    return DampingComparison(
        undamped_results=undamped_results,
        damped_results=damped_results,
        theory=theory,
        table=table,
    )
