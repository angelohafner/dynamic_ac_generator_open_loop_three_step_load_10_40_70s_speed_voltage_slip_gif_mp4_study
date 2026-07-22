"""Result containers and tabular post-processing."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Callable

import numpy as np
import pandas as pd

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.damping import calculate_unregulated_frequency_theory
from dynamic_ac_generator.model_types import FloatArray


@dataclass
class SimulationResults:
    """Container for dynamic simulation results and post-processing helpers."""

    config: SimulationConfig
    time_s: FloatArray
    omega_pu: FloatArray
    integral_state: FloatArray
    mechanical_power_pu: FloatArray
    rotor_angle_rad: FloatArray
    electrical_power_pu: FloatArray
    load_resistance_ohm: FloatArray
    mechanical_power_reference_pu: FloatArray
    field_current_pu: FloatArray
    internal_voltage_ll_rms: FloatArray
    terminal_voltage_ll_rms: FloatArray
    terminal_voltage_phase_rms: FloatArray
    terminal_voltage_angle_rad: FloatArray
    load_current_phase_rms: FloatArray
    state_sampler: Callable[[FloatArray], FloatArray] = field(repr=False)

    @property
    def frequency_hz(self) -> FloatArray:
        """Return generator frequency in hertz."""
        return self.config.F_NOM_HZ * self.omega_pu

    @property
    def frequency_error_hz(self) -> FloatArray:
        """Return nominal frequency minus actual frequency in hertz."""
        return self.config.F_NOM_HZ - self.frequency_hz

    def to_dataframe(self) -> pd.DataFrame:
        """Convert the dynamic simulation results to a Pandas DataFrame."""
        return pd.DataFrame(
            {
                "time_s": self.time_s,
                "frequency_hz": self.frequency_hz,
                "omega_pu": self.omega_pu,
                "frequency_error_hz": self.frequency_error_hz,
                "mechanical_power_pu": self.mechanical_power_pu,
                "electrical_power_pu": self.electrical_power_pu,
                "mechanical_power_reference_pu": self.mechanical_power_reference_pu,
                "field_current_pu": self.field_current_pu,
                "internal_voltage_ll_rms": self.internal_voltage_ll_rms,
                "terminal_voltage_ll_rms": self.terminal_voltage_ll_rms,
                "terminal_voltage_phase_rms": self.terminal_voltage_phase_rms,
                "terminal_voltage_angle_rad": self.terminal_voltage_angle_rad,
                "load_current_phase_rms": self.load_current_phase_rms,
                "load_resistance_ohm": self.load_resistance_ohm,
                "rotor_angle_rad": self.rotor_angle_rad,
                "governor_integral_state": self.integral_state,
            }
        )


def calculate_settling_time(results: SimulationResults) -> float:
    """Return the frequency settling time, or NaN if it is not reached."""
    target_frequency_hz = results.config.F_NOM_HZ
    tolerance_hz = results.config.FREQUENCY_TOLERANCE_HZ
    if results.config.CONTROL_MODE == "unregulated":
        theory = calculate_unregulated_frequency_theory(results.config)
        if theory.has_finite_equilibrium:
            target_frequency_hz = theory.final_frequency_hz
            tolerance_hz = results.config.DAMPING_SETTLING_TOLERANCE_HZ

    frequency_deviation_hz = np.abs(results.frequency_hz - target_frequency_hz)
    after_step_indices = np.flatnonzero(results.time_s >= results.config.LOAD_STEP_TIME_S)
    for index in after_step_indices:
        remains_inside_band = np.all(
            frequency_deviation_hz[index:] <= tolerance_hz
        )
        if remains_inside_band:
            return float(results.time_s[index])
    return math.nan


def format_metric_value(value: float) -> float | str:
    """Format finite numeric values while preserving unavailable metrics."""
    if isinstance(value, float) and math.isnan(value):
        return "Not reached in simulation window"
    return value


def build_summary_table(results: SimulationResults) -> pd.DataFrame:
    """Build the scalar numerical summary table."""
    frequency_hz = results.frequency_hz
    minimum_frequency_index = int(np.argmin(frequency_hz))
    maximum_frequency_index = int(np.argmax(frequency_hz))
    settling_time_s = calculate_settling_time(results)

    theory = calculate_unregulated_frequency_theory(results.config)
    theoretical_final_frequency: float | str = (
        theory.final_frequency_hz
        if theory.has_finite_equilibrium
        else "No finite open-loop equilibrium"
    )
    theoretical_time_constant: float | str = (
        theory.time_constant_s
        if theory.has_finite_equilibrium
        else "Not applicable"
    )
    theoretical_settling_time: float | str = (
        theory.settling_time_s
        if theory.has_finite_equilibrium
        else "Not applicable"
    )

    rows = [
        ("Nominal frequency", results.config.F_NOM_HZ, "Hz"),
        ("Damping coefficient", results.config.D, "pu"),
        ("Minimum frequency", float(frequency_hz[minimum_frequency_index]), "Hz"),
        ("Maximum frequency", float(frequency_hz[maximum_frequency_index]), "Hz"),
        ("Final frequency", float(frequency_hz[-1]), "Hz"),
        ("Theoretical final frequency", theoretical_final_frequency, "Hz"),
        ("Open-loop frequency time constant", theoretical_time_constant, "s"),
        ("Approximate open-loop settling time", theoretical_settling_time, "s"),
        (
            "Maximum frequency deviation",
            float(np.max(np.abs(frequency_hz - results.config.F_NOM_HZ))),
            "Hz",
        ),
        ("Time of minimum frequency", float(results.time_s[minimum_frequency_index]), "s"),
        ("Initial electrical power", float(results.electrical_power_pu[0]), "pu"),
        ("Final electrical power", float(results.electrical_power_pu[-1]), "pu"),
        ("Initial mechanical power", float(results.mechanical_power_pu[0]), "pu"),
        ("Final mechanical power", float(results.mechanical_power_pu[-1]), "pu"),
        ("Initial field current", float(results.field_current_pu[0]), "pu"),
        ("Final field current", float(results.field_current_pu[-1]), "pu"),
        ("Initial internal voltage", float(results.internal_voltage_ll_rms[0]), "V LL RMS"),
        ("Final internal voltage", float(results.internal_voltage_ll_rms[-1]), "V LL RMS"),
        ("Initial terminal voltage", float(results.terminal_voltage_ll_rms[0]), "V LL RMS"),
        ("Final terminal voltage", float(results.terminal_voltage_ll_rms[-1]), "V LL RMS"),
        ("Initial load current", float(results.load_current_phase_rms[0]), "A phase RMS"),
        ("Final load current", float(results.load_current_phase_rms[-1]), "A phase RMS"),
        ("Initial resistance", results.config.initial_resistance_ohm, "ohm"),
        ("Final resistance", results.config.final_resistance_ohm, "ohm"),
        ("Settling time", format_metric_value(settling_time_s), "s"),
        ("Steady-state frequency error", float(results.config.F_NOM_HZ - frequency_hz[-1]), "Hz"),
    ]
    return pd.DataFrame(rows, columns=["metric", "value", "unit"])
