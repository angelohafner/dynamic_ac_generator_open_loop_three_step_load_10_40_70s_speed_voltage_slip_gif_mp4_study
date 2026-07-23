"""Matplotlib figure generation for the dynamic generator simulation."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.damping import DampingComparison, calculate_unregulated_frequency_theory
from dynamic_ac_generator.results import SimulationResults


def _save_current_figure(output_dir: Path, file_name: str) -> Path:
    """Save the current Matplotlib figure and close it."""
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_path = output_dir / file_name
    plt.tight_layout()
    plt.savefig(figure_path, dpi=150, bbox_inches="tight")
    plt.close()
    return figure_path


def _add_load_step_marker(config: SimulationConfig) -> None:
    """Add vertical markers at every load-step time."""
    for step_index, step_time_s in enumerate(config.load_step_times_s, start=1):
        plt.axvline(step_time_s, linestyle="--", label=f"_Load step {step_index}")


def _finish_time_plot(
    config: SimulationConfig,
    output_dir: Path,
    title: str,
    x_label: str,
    y_label: str,
    file_name: str,
) -> Path:
    """Apply common labels, grid, legend, and save the plot."""
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.grid(True, alpha=0.5)
    plt.legend()
    return _save_current_figure(output_dir, file_name)


def generate_all_figures(
    results: SimulationResults,
    waveforms_before: pd.DataFrame,
    waveforms_after: pd.DataFrame,
    waveforms_power: pd.DataFrame,
    output_dir: Path,
) -> list[Path]:
    """Generate and save all required Matplotlib figures."""
    config = results.config
    is_pi_controlled = config.CONTROL_MODE == "pi"
    frequency_title = (
        "PI-Controlled Generator Frequency Versus Time"
        if is_pi_controlled
        else "Unregulated Generator Frequency Versus Time"
    )
    reference_label = "Governor mechanical power reference" if is_pi_controlled else "Constant mechanical power input"
    reference_title = "Mechanical Power Command Versus Time" if is_pi_controlled else "Constant Mechanical Input Versus Time"
    reference_file_name = (
        "06_governor_power_reference.png"
        if is_pi_controlled
        else "06_constant_mechanical_input.png"
    )
    figure_paths: list[Path] = []

    plt.figure(figsize=(9.0, 4.5))
    plt.plot(results.time_s, results.frequency_hz, label="Generator frequency")
    plt.axhline(config.F_NOM_HZ, linestyle="--", label="Nominal frequency")
    _add_load_step_marker(config)
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            frequency_title,
            "Time (s)",
            "Frequency (Hz)",
            "01_generator_frequency.png",
        )
    )

    plt.figure(figsize=(9.0, 4.5))
    plt.plot(results.time_s, results.omega_pu, label="Rotor speed")
    plt.axhline(1.0, linestyle=":", label="Nominal speed")
    _add_load_step_marker(config)
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            "Rotor Speed in Per Unit Versus Time",
            "Time (s)",
            "Rotor speed (pu)",
            "02_rotor_speed_pu.png",
        )
    )

    plt.figure(figsize=(9.0, 4.5))
    plt.plot(results.time_s, results.mechanical_power_pu, label="Mechanical power")
    plt.plot(results.time_s, results.electrical_power_pu, label="Electrical power")
    _add_load_step_marker(config)
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            "Mechanical and Electrical Power Versus Time",
            "Time (s)",
            "Power (pu)",
            "03_mechanical_and_electrical_power.png",
        )
    )

    figure, (impedance_magnitude_axis, impedance_angle_axis) = plt.subplots(
        2,
        1,
        figsize=(9.0, 6.2),
        sharex=True,
    )
    magnitude_line, = impedance_magnitude_axis.plot(
        results.time_s,
        results.load_impedance_magnitude_ohm,
        label="|Z|",
    )
    real_line, = impedance_magnitude_axis.plot(
        results.time_s,
        results.load_impedance_real_ohm,
        label="Re(Z)",
    )
    imaginary_line, = impedance_magnitude_axis.plot(
        results.time_s,
        results.load_impedance_imag_ohm,
        label="Im(Z)",
    )
    angle_line, = impedance_angle_axis.plot(
        results.time_s,
        results.load_impedance_angle_deg,
        color="tab:purple",
        label="Angle",
    )
    for step_index, step_time_s in enumerate(config.load_step_times_s, start=1):
        for axis in (impedance_magnitude_axis, impedance_angle_axis):
            axis.axvline(step_time_s, linestyle="--", label=f"_Load step {step_index}")
    impedance_magnitude_axis.set_title("Load Impedance Magnitude Versus Time")
    impedance_angle_axis.set_title("Load Impedance Angle Versus Time")
    impedance_angle_axis.set_xlabel("Time (s)")
    impedance_magnitude_axis.set_ylabel("Impedance (ohm)")
    impedance_angle_axis.set_ylabel("Angle (deg)")
    for axis in (impedance_magnitude_axis, impedance_angle_axis):
        axis.grid(True, alpha=0.5)
    impedance_magnitude_axis.legend(
        handles=[magnitude_line, real_line, imaginary_line],
        loc="upper right",
    )
    impedance_angle_axis.legend(handles=[angle_line], loc="upper right")
    figure_paths.append(_save_current_figure(output_dir, "04_load_impedance.png"))

    plt.figure(figsize=(9.0, 4.5))
    plt.plot(results.time_s, results.frequency_error_hz, label="Frequency error")
    plt.axhline(0.0, linestyle=":", label="Zero error")
    _add_load_step_marker(config)
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            "Frequency Error Versus Time",
            "Time (s)",
            "Nominal minus actual frequency (Hz)",
            "05_frequency_error.png",
        )
    )

    plt.figure(figsize=(9.0, 4.5))
    plt.plot(results.time_s, results.mechanical_power_reference_pu, label=reference_label)
    _add_load_step_marker(config)
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            reference_title,
            "Time (s)",
            "Mechanical power command (pu)",
            reference_file_name,
        )
    )

    plt.figure(figsize=(9.0, 4.5))
    plt.plot(results.time_s, results.rotor_angle_rad, label="Rotor electrical angle")
    _add_load_step_marker(config)
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            "Rotor Electrical Angle Versus Time",
            "Time (s)",
            "Rotor electrical angle (rad)",
            "07_rotor_angle.png",
        )
    )

    plt.figure(figsize=(9.0, 4.5))
    plt.plot(waveforms_before["time_s"], waveforms_before["voltage_a_v"], label="Phase A voltage")
    plt.plot(waveforms_before["time_s"], waveforms_before["voltage_b_v"], label="Phase B voltage")
    plt.plot(waveforms_before["time_s"], waveforms_before["voltage_c_v"], label="Phase C voltage")
    _add_load_step_marker(config)
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            "Three-Phase Voltages Before the Load Step",
            "Time (s)",
            "Voltage (V)",
            "08_three_phase_voltages_before_step.png",
        )
    )

    plt.figure(figsize=(9.0, 4.5))
    plt.plot(waveforms_after["time_s"], waveforms_after["voltage_a_v"], label="Phase A voltage")
    plt.plot(waveforms_after["time_s"], waveforms_after["voltage_b_v"], label="Phase B voltage")
    plt.plot(waveforms_after["time_s"], waveforms_after["voltage_c_v"], label="Phase C voltage")
    _add_load_step_marker(config)
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            "Three-Phase Voltages After the Load Step",
            "Time (s)",
            "Voltage (V)",
            "09_three_phase_voltages_after_step.png",
        )
    )

    plt.figure(figsize=(9.0, 4.5))
    plt.plot(waveforms_after["time_s"], waveforms_after["current_a_a"], label="Phase A current")
    plt.plot(waveforms_after["time_s"], waveforms_after["current_b_a"], label="Phase B current")
    plt.plot(waveforms_after["time_s"], waveforms_after["current_c_a"], label="Phase C current")
    _add_load_step_marker(config)
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            "Three-Phase Currents After the Load Step",
            "Time (s)",
            "Current (A)",
            "10_three_phase_currents_after_step.png",
        )
    )

    plt.figure(figsize=(9.0, 4.5))
    plt.plot(waveforms_power["time_s"], waveforms_power["total_power_pu"], label="Total three-phase power")
    _add_load_step_marker(config)
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            "Instantaneous Three-Phase Electrical Power",
            "Time (s)",
            "Power (pu)",
            "11_instantaneous_three_phase_power.png",
        )
    )

    plt.figure(figsize=(9.0, 4.5))
    plt.plot(waveforms_after["time_s"], waveforms_after["voltage_a_v"], label="Phase A voltage")
    _add_load_step_marker(config)
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            "Phase A Voltage After the Load Step",
            "Time (s)",
            "Voltage (V)",
            "12_phase_a_voltage_after_step.png",
        )
    )

    plt.figure(figsize=(9.0, 4.5))
    plt.plot(waveforms_after["time_s"], waveforms_after["current_a_a"], label="Phase A current")
    _add_load_step_marker(config)
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            "Phase A Current After the Load Step",
            "Time (s)",
            "Current (A)",
            "13_phase_a_current_after_step.png",
        )
    )

    plt.figure(figsize=(9.0, 4.5))
    plt.plot(results.time_s, results.frequency_hz, label="Generator frequency")
    plt.axhline(config.F_NOM_HZ, linestyle="--", label="Nominal frequency")
    if is_pi_controlled:
        plt.axhline(
            config.F_NOM_HZ + config.FREQUENCY_TOLERANCE_HZ,
            linestyle=":",
            label="Upper settling band",
        )
        plt.axhline(
            config.F_NOM_HZ - config.FREQUENCY_TOLERANCE_HZ,
            linestyle=":",
            label="Lower settling band",
        )
    _add_load_step_marker(config)
    response_title = (
        "PI Frequency Response With Settling Band"
        if is_pi_controlled
        else "Unregulated Frequency Response After Load Changes"
    )
    response_file_name = (
        "14_pi_frequency_settling_band.png"
        if is_pi_controlled
        else "14_unregulated_frequency_response.png"
    )
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            response_title,
            "Time (s)",
            "Frequency (Hz)",
            response_file_name,
        )
    )

    plt.figure(figsize=(9.0, 4.5))
    plt.plot(results.time_s, results.internal_voltage_ll_rms, label="Internal generated voltage")
    plt.plot(results.time_s, results.terminal_voltage_ll_rms, label="Terminal voltage")
    plt.axhline(config.V_LL_RMS, linestyle="--", label="Nominal terminal voltage")
    _add_load_step_marker(config)
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            "Open-Loop Internal and Terminal Voltage",
            "Time (s)",
            "Voltage (V LL RMS)",
            "17_open_loop_internal_terminal_voltage.png",
        )
    )

    plt.figure(figsize=(9.0, 4.5))
    plt.plot(results.time_s, results.load_current_phase_rms, label="Load current")
    plt.plot(results.time_s, results.field_current_pu, label="Field current")
    _add_load_step_marker(config)
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            "Open-Loop Load Current and Field Current",
            "Time (s)",
            "Current (A phase RMS or pu field)",
            "18_open_loop_load_current_field_current.png",
        )
    )

    return figure_paths


def generate_damping_comparison_figures(
    comparison: DampingComparison,
    output_dir: Path,
) -> list[Path]:
    """Generate comparison figures for D=0 and D>0 unregulated cases."""
    table = comparison.table
    config = comparison.damped_results.config
    figure_paths: list[Path] = []

    plt.figure(figsize=(9.0, 4.8))
    plt.plot(table["time_s"], table["frequency_no_damping_hz"], label="No damping, D = 0")
    plt.plot(
        table["time_s"],
        table["frequency_with_damping_hz"],
        label=f"With damping, D = {config.D:.2f}",
    )
    plt.axhline(config.F_NOM_HZ, linestyle="--", label="Nominal frequency")
    plt.axhline(
        comparison.theory.final_frequency_hz,
        linestyle="--",
        label=f"Expected damped final frequency = {comparison.theory.final_frequency_hz:.2f} Hz",
    )
    _add_load_step_marker(config)
    if comparison.theory.has_finite_equilibrium:
        plt.axvline(
            comparison.theory.settling_time_s,
            linestyle="-.",
            label=f"Approx. settling = {comparison.theory.settling_time_s:.2f} s",
        )
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            "Unregulated Frequency: No Damping Versus Damped Load Response",
            "Time (s)",
            "Frequency (Hz)",
            "15_unregulated_damping_frequency_comparison.png",
        )
    )

    plt.figure(figsize=(9.0, 4.8))
    plt.plot(
        table["time_s"],
        table["accelerating_power_no_damping_pu"],
        label="Net accelerating power, D = 0",
    )
    plt.plot(
        table["time_s"],
        table["accelerating_power_with_damping_pu"],
        label=f"Net accelerating power, D = {config.D:.2f}",
    )
    plt.plot(
        table["time_s"],
        table["power_imbalance_with_damping_pu"],
        linestyle=":",
        label="Raw Pm - Pe",
    )
    plt.axhline(0.0, linestyle="--", label="Zero acceleration")
    _add_load_step_marker(config)
    figure_paths.append(
        _finish_time_plot(
            config,
            output_dir,
            "Power Imbalance and Damping Torque Effect",
            "Time (s)",
            "Power balance term (pu)",
            "16_unregulated_damping_power_imbalance_comparison.png",
        )
    )

    return figure_paths


def generate_open_loop_equilibrium_curve_figure(
    config: SimulationConfig,
    curve: pd.DataFrame,
    output_dir: Path,
) -> Path:
    """Generate Pe versus speed figure for old and speed-coupled voltage models."""
    theory = calculate_unregulated_frequency_theory(config)
    plt.figure(figsize=(9.0, 4.8))
    plt.plot(
        curve["frequency_hz"],
        curve["electrical_power_if_only_pu"],
        label="Old model: E = Ke If",
    )
    plt.plot(
        curve["frequency_hz"],
        curve["electrical_power_speed_coupled_pu"],
        label="New model: E = Ke If omega",
    )
    plt.plot(
        curve["frequency_hz"],
        curve["mechanical_power_pu"],
        linestyle="--",
        label="Constant mechanical power",
    )
    if theory.has_finite_equilibrium:
        plt.axvline(
            theory.final_frequency_hz,
            linestyle=":",
            label=f"Pe = Pm at {theory.final_frequency_hz:.2f} Hz",
        )
    plt.title("Open-Loop Electrical Power Versus Speed")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Power (pu)")
    plt.grid(True, alpha=0.5)
    plt.legend(loc="upper left")
    return _save_current_figure(
        output_dir,
        "19_open_loop_power_speed_equilibrium.png",
    )
