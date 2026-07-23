"""Automatic validation checks for the generator simulation."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from dynamic_ac_generator.damping import calculate_unregulated_frequency_theory
from dynamic_ac_generator.model_types import FloatArray
from dynamic_ac_generator.results import SimulationResults


def classify_check(pass_condition: bool, warning_condition: bool = False) -> str:
    """Return a PASS, WARNING, or FAIL status string."""
    if pass_condition:
        return "PASS"
    if warning_condition:
        return "WARNING"
    return "FAIL"


def estimate_phase_displacement_degrees(reference_v: FloatArray, shifted_v: FloatArray) -> float:
    """Estimate phase displacement using normalized waveform correlation."""
    centered_reference = reference_v - np.mean(reference_v)
    centered_shifted = shifted_v - np.mean(shifted_v)
    correlation = np.dot(centered_reference, centered_shifted) / (
        np.linalg.norm(centered_reference) * np.linalg.norm(centered_shifted)
    )
    bounded_correlation = float(np.clip(correlation, -1.0, 1.0))
    return math.degrees(math.acos(bounded_correlation))


def build_validation_report(
    results: SimulationResults,
    waveform_window: pd.DataFrame,
) -> pd.DataFrame:
    """Run automatic validation checks and return a concise report."""
    frequency_hz = results.frequency_hz
    step_index = int(np.searchsorted(results.time_s, results.config.LOAD_STEP_TIME_S))
    after_step_index = int(np.searchsorted(results.time_s, results.config.LOAD_STEP_TIME_S + 0.20))
    sign_index = int(np.searchsorted(results.time_s, results.config.LOAD_STEP_TIME_S + 0.02))

    initial_frequency_error_hz = abs(float(frequency_hz[0] - results.config.F_NOM_HZ))
    initial_power_error_pu = abs(float(results.mechanical_power_pu[0] - results.electrical_power_pu[0]))
    first_step_frequency_change_hz = float(frequency_hz[after_step_index] - frequency_hz[step_index])
    mechanical_power_increase_pu = float(results.mechanical_power_pu[-1] - results.mechanical_power_pu[0])
    mechanical_power_change_pu = abs(mechanical_power_increase_pu)
    mechanical_power_response_span_pu = float(
        np.max(results.mechanical_power_pu) - np.min(results.mechanical_power_pu)
    )
    final_frequency_error_hz = abs(float(frequency_hz[-1] - results.config.F_NOM_HZ))
    initial_terminal_voltage_error_v = abs(float(results.terminal_voltage_ll_rms[0] - results.config.V_LL_RMS))
    field_current_change_pu = abs(float(results.field_current_pu[-1] - results.field_current_pu[0]))
    terminal_voltage_drop_v = float(results.terminal_voltage_ll_rms[0] - results.terminal_voltage_ll_rms[step_index + 1])

    phase_ab_degrees = estimate_phase_displacement_degrees(
        waveform_window["voltage_a_v"].to_numpy(dtype=float),
        waveform_window["voltage_b_v"].to_numpy(dtype=float),
    )
    phase_ac_degrees = estimate_phase_displacement_degrees(
        waveform_window["voltage_a_v"].to_numpy(dtype=float),
        waveform_window["voltage_c_v"].to_numpy(dtype=float),
    )
    maximum_phase_error_degrees = max(
        abs(phase_ab_degrees - 120.0),
        abs(phase_ac_degrees - 120.0),
    )

    power_mean_w = float(waveform_window["total_power_w"].mean())
    power_std_w = float(waveform_window["total_power_w"].std())
    relative_power_std = power_std_w / abs(power_mean_w)

    power_imbalance_pu = float(results.mechanical_power_pu[sign_index] - results.electrical_power_pu[sign_index])
    measured_speed_derivative_pu_per_s = float(
        (results.omega_pu[sign_index + 1] - results.omega_pu[sign_index - 1])
        / (results.time_s[sign_index + 1] - results.time_s[sign_index - 1])
    )
    sign_consistent = (
        abs(power_imbalance_pu) > 1e-9
        and power_imbalance_pu * measured_speed_derivative_pu_per_s > 0.0
    )
    second_step_frequency_change_hz = math.nan
    if results.config.CONTROL_MODE == "unregulated" and len(results.config.load_step_times_s) > 1:
        second_step_time_s = results.config.load_step_times_s[1]
        second_step_index = int(np.searchsorted(results.time_s, second_step_time_s))
        after_second_step_index = int(np.searchsorted(results.time_s, second_step_time_s + 0.20))
        second_step_frequency_change_hz = float(
            frequency_hz[after_second_step_index] - frequency_hz[second_step_index]
        )
    third_step_frequency_change_hz = math.nan
    if results.config.CONTROL_MODE == "unregulated" and len(results.config.load_step_times_s) > 2:
        third_step_time_s = results.config.load_step_times_s[2]
        third_step_index = int(np.searchsorted(results.time_s, third_step_time_s))
        after_third_step_index = int(np.searchsorted(results.time_s, third_step_time_s + 0.20))
        third_step_frequency_change_hz = float(
            frequency_hz[after_third_step_index] - frequency_hz[third_step_index]
        )

    if results.config.CONTROL_MODE == "pi":
        mechanical_power_row = {
            "status": classify_check(mechanical_power_response_span_pu > 0.20),
            "check": "Mechanical power responds to the load disturbances",
            "value": mechanical_power_response_span_pu,
            "unit": "pu span",
        }
        final_frequency_row = {
            "status": classify_check(
                final_frequency_error_hz <= 0.10,
                warning_condition=final_frequency_error_hz <= 0.50,
            ),
            "check": "Final frequency returns close to 60 Hz",
            "value": final_frequency_error_hz,
            "unit": "Hz error",
        }
    else:
        theory = calculate_unregulated_frequency_theory(results.config)
        theoretical_final_error_hz = abs(float(frequency_hz[-1] - theory.final_frequency_hz))
        mechanical_power_row = {
            "status": classify_check(mechanical_power_change_pu <= 1e-9),
            "check": "Mechanical power remains constant without a speed regulator",
            "value": mechanical_power_change_pu,
            "unit": "pu change",
        }
        final_frequency_row = {
            "status": classify_check(
                theory.has_finite_equilibrium
                and theoretical_final_error_hz <= results.config.DAMPING_SETTLING_TOLERANCE_HZ,
                warning_condition=theory.has_finite_equilibrium
                and theoretical_final_error_hz <= 5.0 * results.config.DAMPING_SETTLING_TOLERANCE_HZ,
            ),
            "check": "Final frequency reaches the theoretical open-loop equilibrium",
            "value": theoretical_final_error_hz,
            "unit": "Hz error",
        }

    report_rows = [
        {
            "status": classify_check(initial_frequency_error_hz <= 1e-9),
            "check": "Initial frequency is approximately 60 Hz",
            "value": initial_frequency_error_hz,
            "unit": "Hz error",
        },
        {
            "status": classify_check(initial_power_error_pu <= 1e-9),
            "check": "Initial mechanical and electrical powers are equal",
            "value": initial_power_error_pu,
            "unit": "pu error",
        },
        {
            "status": classify_check(first_step_frequency_change_hz > 0.01),
            "check": "Frequency initially increases after the first impedance change",
            "value": first_step_frequency_change_hz,
            "unit": "Hz change",
        },
        mechanical_power_row,
        {
            "status": classify_check(initial_terminal_voltage_error_v <= 1e-9),
            "check": "Initial terminal voltage is nominal in open-loop excitation",
            "value": initial_terminal_voltage_error_v,
            "unit": "V LL RMS error",
        },
        {
            "status": classify_check(field_current_change_pu <= 1e-12),
            "check": "Field current remains constant in open-loop excitation",
            "value": field_current_change_pu,
            "unit": "pu change",
        },
        {
            "status": classify_check(terminal_voltage_drop_v > 1.0),
            "check": "Terminal voltage drops after the first impedance change",
            "value": terminal_voltage_drop_v,
            "unit": "V LL RMS drop",
        },
        final_frequency_row,
        *(
            [
                {
                    "status": classify_check(
                        second_step_frequency_change_hz < -0.01
                    ),
                    "check": "Frequency decreases after the second impedance change",
                    "value": second_step_frequency_change_hz,
                    "unit": "Hz change",
                }
            ]
            if results.config.CONTROL_MODE == "unregulated" and len(results.config.load_step_times_s) > 1
            else []
        ),
        *(
            [
                {
                    "status": classify_check(
                        third_step_frequency_change_hz > 0.01
                    ),
                    "check": "Frequency increases after the third load restoration",
                    "value": third_step_frequency_change_hz,
                    "unit": "Hz change",
                }
            ]
            if results.config.CONTROL_MODE == "unregulated" and len(results.config.load_step_times_s) > 2
            else []
        ),
        {
            "status": classify_check(maximum_phase_error_degrees <= 1.0),
            "check": "Three phase voltages are displaced by approximately 120 degrees",
            "value": maximum_phase_error_degrees,
            "unit": "degree error",
        },
        {
            "status": classify_check(
                relative_power_std <= 1e-2,
                warning_condition=relative_power_std <= 2e-2,
            ),
            "check": "Total instantaneous power varies smoothly for a balanced impedance load",
            "value": relative_power_std,
            "unit": "relative standard deviation",
        },
        {
            "status": classify_check(sign_consistent),
            "check": "Energy and power signs are consistent immediately after the disturbance",
            "value": measured_speed_derivative_pu_per_s,
            "unit": "pu/s speed derivative",
        },
    ]
    return pd.DataFrame(report_rows)
