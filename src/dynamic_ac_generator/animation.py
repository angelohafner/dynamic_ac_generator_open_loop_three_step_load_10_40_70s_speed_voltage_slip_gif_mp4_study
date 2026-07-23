"""Animated Matplotlib visualizations for dynamic generator cases."""

from __future__ import annotations

from pathlib import Path
import math

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter
from matplotlib.patches import Polygon
import numpy as np

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.damping import DampingComparison
from dynamic_ac_generator.model_types import FloatArray
from dynamic_ac_generator.results import SimulationResults
from dynamic_ac_generator.simulation import DynamicSimulation


def build_animation_frame_times(
    config: SimulationConfig,
    frame_count: int | None = None,
) -> FloatArray:
    """Build monotonically increasing animation frame times including all load steps."""
    active_frame_count = frame_count if frame_count is not None else config.ANIMATION_FRAME_COUNT
    if active_frame_count < 3:
        raise ValueError("Animation frame count must be at least 3.")

    base_times = np.linspace(0.0, config.SIMULATION_TIME_S, active_frame_count, dtype=float)
    frame_times = np.unique(
        np.concatenate(
            [
                base_times,
                np.array([0.0, *config.load_step_times_s, config.SIMULATION_TIME_S], dtype=float),
            ]
        )
    )
    return frame_times.astype(float)


def build_rotor_animation_frame_times(
    config: SimulationConfig,
    frame_count: int | None = None,
) -> FloatArray:
    """Build dense rotor animation frame times focused around the load step."""
    active_frame_count = frame_count if frame_count is not None else config.ROTOR_ANIMATION_FRAME_COUNT
    if active_frame_count < 3:
        raise ValueError("Rotor animation frame count must be at least 3.")

    start_s = config.LOAD_STEP_TIME_S - config.ROTOR_ANIMATION_PRE_STEP_TIME_S
    end_s = config.LOAD_STEP_TIME_S + config.ROTOR_ANIMATION_POST_STEP_TIME_S
    bounded_start_s = max(0.0, start_s)
    bounded_end_s = min(config.SIMULATION_TIME_S, end_s)
    if bounded_end_s <= bounded_start_s:
        raise ValueError("Rotor animation focused time window is invalid.")

    base_times = np.linspace(bounded_start_s, bounded_end_s, active_frame_count, dtype=float)
    frame_times = np.unique(
        np.concatenate(
            [
                base_times,
                np.array([config.LOAD_STEP_TIME_S], dtype=float),
            ]
        )
    )
    return frame_times.astype(float)


def build_slip_animation_frame_times(
    config: SimulationConfig,
    frame_count: int | None = None,
) -> FloatArray:
    """Build frame times for the rotor-reference slip animation around load changes."""
    active_frame_count = frame_count if frame_count is not None else config.SLIP_ANIMATION_FRAME_COUNT
    if active_frame_count < 3:
        raise ValueError("Slip animation frame count must be at least 3.")

    start_s = max(0.0, config.LOAD_STEP_TIME_S - config.SLIP_ANIMATION_PRE_STEP_TIME_S)
    end_s = min(config.SIMULATION_TIME_S, config.LOAD_STEP_TIME_S + config.SLIP_ANIMATION_DURATION_S)
    if end_s <= start_s:
        raise ValueError("Slip animation time window is invalid.")

    base_times = np.linspace(start_s, end_s, active_frame_count, dtype=float)
    included_step_times_s = np.array(
        [
            step_time_s
            for step_time_s in config.load_step_times_s
            if start_s <= step_time_s <= end_s
        ],
        dtype=float,
    )
    frame_times = np.unique(
        np.concatenate(
            [
                base_times,
                np.array([start_s, end_s], dtype=float),
                included_step_times_s,
            ]
        )
    )
    return frame_times.astype(float)


def calculate_slow_motion_reference_angle(
    config: SimulationConfig,
    frame_times_s: FloatArray,
) -> FloatArray:
    """Calculate the slow-motion reference angle used for didactic display."""
    frame_time_array_s = np.asarray(frame_times_s, dtype=float)
    time_offset_s = frame_time_array_s - frame_time_array_s[0]
    reference_angle_rad = (
        2.0
        * math.pi
        * config.SLOW_MOTION_REFERENCE_FREQUENCY_HZ
        * time_offset_s
    )
    return reference_angle_rad.astype(float)


def calculate_slow_motion_display_angles(
    results: SimulationResults,
    frame_times_s: FloatArray,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Calculate slow counterclockwise reference and rotor display angles."""
    omega_pu = np.interp(frame_times_s, results.time_s, results.omega_pu).astype(float)
    time_step_s = np.diff(frame_times_s)
    average_speed_pu = 0.5 * (omega_pu[1:] + omega_pu[:-1])
    angle_increments_rad = (
        2.0
        * math.pi
        * results.config.SLOW_MOTION_REFERENCE_FREQUENCY_HZ
        * average_speed_pu
        * time_step_s
    )
    reference_angle_rad = calculate_slow_motion_reference_angle(results.config, frame_times_s)
    rotor_angle_rad = np.zeros_like(frame_times_s, dtype=float)
    rotor_angle_rad[1:] = np.cumsum(angle_increments_rad)
    lead_cycles = (reference_angle_rad - rotor_angle_rad) / (2.0 * math.pi)
    return reference_angle_rad.astype(float), rotor_angle_rad.astype(float), lead_cycles.astype(float)


def calculate_slow_motion_rotor_angle(
    results: SimulationResults,
    frame_times_s: FloatArray,
) -> FloatArray:
    """Calculate a slow-motion display angle for the electrical rotor pointer."""
    omega_pu = np.interp(frame_times_s, results.time_s, results.omega_pu).astype(float)
    time_step_s = np.diff(frame_times_s)
    average_speed_pu = 0.5 * (omega_pu[1:] + omega_pu[:-1])
    angle_increments_rad = (
        2.0
        * math.pi
        * results.config.ROTOR_DISPLAY_FREQUENCY_HZ
        * average_speed_pu
        * time_step_s
    )
    display_angle_rad = np.zeros_like(frame_times_s, dtype=float)
    display_angle_rad[1:] = np.cumsum(angle_increments_rad)
    return display_angle_rad


def calculate_synchronous_reference_angle(
    config: SimulationConfig,
    frame_times_s: FloatArray,
) -> FloatArray:
    """Calculate the ideal synchronous reference angle at frame times."""
    frame_time_array_s = np.asarray(frame_times_s, dtype=float)
    time_offset_s = frame_time_array_s - frame_time_array_s[0]
    reference_angle_rad = 2.0 * math.pi * config.ROTOR_DISPLAY_FREQUENCY_HZ * time_offset_s
    return reference_angle_rad.astype(float)


def calculate_rotor_reference_lag(
    results: SimulationResults,
    frame_times_s: FloatArray,
) -> FloatArray:
    """Calculate accumulated 60 Hz reference angle minus actual rotor angle."""
    reference_angle_rad = calculate_synchronous_reference_angle(results.config, frame_times_s)
    rotor_angle_rad = calculate_slow_motion_rotor_angle(results, frame_times_s)
    lag_rad = reference_angle_rad - rotor_angle_rad
    return lag_rad.astype(float)


def calculate_rotating_reference_vector(
    angle_rad: FloatArray,
    radius: float = 1.05,
) -> tuple[FloatArray, FloatArray]:
    """Return x and y coordinates for a rotating radial reference vector."""
    angle_array_rad = np.asarray(angle_rad, dtype=float)
    x_values = np.column_stack(
        [
            np.zeros_like(angle_array_rad),
            radius * np.cos(angle_array_rad),
        ]
    )
    y_values = np.column_stack(
        [
            np.zeros_like(angle_array_rad),
            radius * np.sin(angle_array_rad),
        ]
    )
    return x_values.astype(float), y_values.astype(float)


def calculate_lag_sector_points(
    reference_angle_rad: float,
    rotor_angle_rad: float,
    radius: float = 0.72,
    sample_count: int = 48,
) -> tuple[FloatArray, FloatArray]:
    """Return polygon points for the shaded rotor lag sector."""
    if sample_count < 2:
        raise ValueError("Lag sector sample count must be at least 2.")
    lead_rad = (reference_angle_rad - rotor_angle_rad + math.pi) % (2.0 * math.pi) - math.pi
    arc_angles_rad = np.linspace(rotor_angle_rad, rotor_angle_rad + lead_rad, sample_count, dtype=float)
    arc_x_values = radius * np.cos(arc_angles_rad)
    arc_y_values = radius * np.sin(arc_angles_rad)
    x_values = np.concatenate([np.array([0.0], dtype=float), arc_x_values, np.array([0.0], dtype=float)])
    y_values = np.concatenate([np.array([0.0], dtype=float), arc_y_values, np.array([0.0], dtype=float)])
    return x_values.astype(float), y_values.astype(float)


def calculate_lag_sector_alpha(
    lead_cycles: float,
    base_alpha: float = 0.20,
    alpha_per_cycle: float = 0.10,
    max_alpha: float = 0.80,
) -> float:
    """Return lag-sector opacity from the accumulated lead or lag in cycles."""
    if not (0.0 <= base_alpha <= max_alpha <= 1.0):
        raise ValueError("Lag-sector alpha limits must satisfy 0 <= base <= max <= 1.")
    if alpha_per_cycle < 0.0:
        raise ValueError("Lag-sector alpha slope cannot be negative.")
    alpha = base_alpha + alpha_per_cycle * abs(float(lead_cycles))
    return float(np.clip(alpha, base_alpha, max_alpha))


def _interpolate(values: FloatArray, source_time_s: FloatArray, frame_times_s: FloatArray) -> FloatArray:
    """Interpolate a time-series at animation frame times."""
    return np.interp(frame_times_s, source_time_s, values).astype(float)


def _save_animation(
    animation: FuncAnimation,
    output_path: Path,
    config: SimulationConfig,
    fps: int | None = None,
) -> Path:
    """Save a Matplotlib animation as a GIF file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    active_fps = fps if fps is not None else config.ANIMATION_FPS
    gif_writer = PillowWriter(fps=active_fps)
    try:
        animation.save(output_path, writer=gif_writer, dpi=config.ANIMATION_DPI)
    finally:
        plt.close(animation._fig)
    return output_path


def _save_mp4_animation(
    animation: FuncAnimation,
    output_path: Path,
    config: SimulationConfig,
    fps: int | None = None,
) -> Path:
    """Save a Matplotlib animation directly as MP4 and remove a stale paired GIF."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    active_fps = fps if fps is not None else config.ANIMATION_FPS
    stale_gif_path = output_path.with_suffix(".gif")
    if stale_gif_path.exists():
        stale_gif_path.unlink()
    mp4_writer = FFMpegWriter(
        fps=active_fps,
        codec="libx264",
        extra_args=["-pix_fmt", "yuv420p"],
    )
    try:
        animation.save(output_path, writer=mp4_writer, dpi=config.ANIMATION_DPI)
    finally:
        plt.close(animation._fig)
    return output_path


def _fixed_legend(axis, location: str) -> None:
    """Add a legend at a fixed location so it does not move during animation."""
    axis.legend(loc=location)


def _enable_grid(axis) -> None:
    """Enable grid lines with the project visual opacity."""
    axis.grid(True, alpha=0.5)


def _add_load_step_markers(axis, config: SimulationConfig, reference_time_s: float = 0.0) -> None:
    """Add fixed vertical markers for every configured load step."""
    for step_index, step_time_s in enumerate(config.load_step_times_s, start=1):
        axis.axvline(
            step_time_s - reference_time_s,
            linestyle=":",
            label=f"_Load step {step_index}",
        )


def _axis_limits(values: FloatArray, padding_fraction: float = 0.08) -> tuple[float, float]:
    """Return padded axis limits for one numeric series."""
    minimum_value = float(np.min(values))
    maximum_value = float(np.max(values))
    span = maximum_value - minimum_value
    if span == 0.0:
        span = abs(maximum_value) if maximum_value != 0.0 else 1.0
    padding = span * padding_fraction
    return minimum_value - padding, maximum_value + padding


def generate_frequency_power_animation(
    results: SimulationResults,
    output_dir: Path,
    frame_times_s: FloatArray | None = None,
) -> Path:
    """Animate frequency, power balance, and load resistance through time."""
    config = results.config
    is_pi_controlled = config.CONTROL_MODE == "pi"
    animation_title = (
        "PI Governor Frequency and Active-Power Balance"
        if is_pi_controlled
        else "Unregulated Frequency Settling After Load Changes"
    )
    reference_label = "Governor reference" if is_pi_controlled else "Constant mechanical input"
    faded_reference_label = "_Full governor reference" if is_pi_controlled else "_Full constant mechanical input"
    file_name = (
        "01_pi_frequency_power_balance.gif"
        if is_pi_controlled
        else "01_unregulated_frequency_power_balance.gif"
    )
    active_frame_times_s = (
        frame_times_s if frame_times_s is not None else build_animation_frame_times(config)
    )
    frame_frequency_hz = _interpolate(results.frequency_hz, results.time_s, active_frame_times_s)
    frame_mechanical_power_pu = _interpolate(
        results.mechanical_power_pu,
        results.time_s,
        active_frame_times_s,
    )
    frame_electrical_power_pu = _interpolate(
        results.electrical_power_pu,
        results.time_s,
        active_frame_times_s,
    )
    frame_reference_power_pu = _interpolate(
        results.mechanical_power_reference_pu,
        results.time_s,
        active_frame_times_s,
    )
    frame_resistance_ohm = _interpolate(results.load_resistance_ohm, results.time_s, active_frame_times_s)

    figure, axes = plt.subplots(3, 1, figsize=(9.5, 7.0), sharex=True)
    frequency_axis, power_axis, resistance_axis = axes

    frequency_axis.plot(results.time_s, results.frequency_hz, alpha=0.25, label="_Full frequency")
    power_axis.plot(results.time_s, results.mechanical_power_pu, alpha=0.25, label="_Full mechanical power")
    power_axis.plot(results.time_s, results.electrical_power_pu, alpha=0.25, label="_Full electrical power")
    power_axis.plot(
        results.time_s,
        results.mechanical_power_reference_pu,
        alpha=0.25,
        label=faded_reference_label,
    )
    resistance_axis.plot(results.time_s, results.load_resistance_ohm, alpha=0.25, label="_Full resistance")

    active_frequency_line, = frequency_axis.plot([], [], label="Animated frequency")
    active_mechanical_line, = power_axis.plot([], [], label="Mechanical power")
    active_electrical_line, = power_axis.plot([], [], label="Electrical power")
    active_reference_line, = power_axis.plot([], [], label=reference_label)
    active_resistance_line, = resistance_axis.plot([], [], label="Load resistance")

    frequency_marker = frequency_axis.axvline(0.0, linestyle="--", label="_Current time")
    power_marker = power_axis.axvline(0.0, linestyle="--", label="_Current time")
    resistance_marker = resistance_axis.axvline(0.0, linestyle="--", label="_Current time")

    frequency_axis.axhline(config.F_NOM_HZ, linestyle="--", label="Nominal frequency")
    for axis in axes:
        _add_load_step_markers(axis, config)
        _enable_grid(axis)
    _fixed_legend(frequency_axis, "upper right")
    _fixed_legend(power_axis, "upper right")
    _fixed_legend(resistance_axis, "upper right")

    frequency_axis.set_ylabel("Frequency (Hz)")
    power_axis.set_ylabel("Power (pu)")
    resistance_axis.set_ylabel("Resistance (ohm)")
    resistance_axis.set_xlabel("Time (s)")
    frequency_axis.set_title(animation_title)
    frequency_axis.set_ylim(*_axis_limits(results.frequency_hz))
    power_axis.set_ylim(
        *_axis_limits(
            np.concatenate(
                [
                    results.mechanical_power_pu,
                    results.electrical_power_pu,
                    results.mechanical_power_reference_pu,
                ]
            )
        )
    )
    resistance_axis.set_ylim(*_axis_limits(results.load_resistance_ohm))
    resistance_axis.set_xlim(0.0, config.SIMULATION_TIME_S)

    def update(frame_index: int) -> list[object]:
        current_time_s = active_frame_times_s[frame_index]
        current_slice = slice(0, frame_index + 1)
        active_frequency_line.set_data(active_frame_times_s[current_slice], frame_frequency_hz[current_slice])
        active_mechanical_line.set_data(
            active_frame_times_s[current_slice],
            frame_mechanical_power_pu[current_slice],
        )
        active_electrical_line.set_data(
            active_frame_times_s[current_slice],
            frame_electrical_power_pu[current_slice],
        )
        active_reference_line.set_data(
            active_frame_times_s[current_slice],
            frame_reference_power_pu[current_slice],
        )
        active_resistance_line.set_data(
            active_frame_times_s[current_slice],
            frame_resistance_ohm[current_slice],
        )
        for marker in [frequency_marker, power_marker, resistance_marker]:
            marker.set_xdata([current_time_s, current_time_s])
        return [
            active_frequency_line,
            active_mechanical_line,
            active_electrical_line,
            active_reference_line,
            active_resistance_line,
            frequency_marker,
            power_marker,
            resistance_marker,
        ]

    animation = FuncAnimation(
        figure,
        update,
        frames=len(active_frame_times_s),
        interval=1000.0 / config.ANIMATION_FPS,
        blit=False,
    )
    figure.tight_layout()
    return _save_animation(animation, output_dir / file_name, config)


def generate_rotor_waveform_animation(
    simulation: DynamicSimulation,
    results: SimulationResults,
    output_dir: Path,
    frame_times_s: FloatArray | None = None,
) -> Path:
    """Animate rotor angle and instantaneous three-phase voltage/current waveforms."""
    config = results.config
    active_frame_times_s = (
        frame_times_s if frame_times_s is not None else build_rotor_animation_frame_times(config)
    )
    rotor_angle_rad = calculate_slow_motion_rotor_angle(results, active_frame_times_s)
    reference_angle_rad = calculate_synchronous_reference_angle(config, active_frame_times_s)
    half_window_s = config.ANIMATION_WAVEFORM_WINDOW_S / 2.0
    relative_time_s = np.linspace(-half_window_s, half_window_s, 220, dtype=float)

    figure = plt.figure(figsize=(10.0, 6.2))
    grid = figure.add_gridspec(2, 2, width_ratios=[1.0, 1.65])
    rotor_axis = figure.add_subplot(grid[:, 0])
    voltage_axis = figure.add_subplot(grid[0, 1])
    current_axis = figure.add_subplot(grid[1, 1], sharex=voltage_axis)

    angle = np.linspace(0.0, 2.0 * math.pi, 400, dtype=float)
    rotor_axis.plot(np.cos(angle), np.sin(angle), label="_Reference circle")
    rotor_axis.axhline(0.0, linewidth=0.8)
    rotor_axis.axvline(0.0, linewidth=0.8)
    electrical_reference_line, = rotor_axis.plot(
        [],
        [],
        linestyle="--",
        label="Electrical reference",
    )
    rotor_line, = rotor_axis.plot([], [], marker="o", linewidth=2.0, label="Rotor angle")
    rotor_axis.set_aspect("equal", adjustable="box")
    rotor_axis.set_xlim(-1.2, 1.2)
    rotor_axis.set_ylim(-1.2, 1.2)
    rotor_axis.set_title("Rotor Electrical Angle (Slow-Motion Display)")
    rotor_axis.set_xlabel(r"$\cos(\theta)$")
    rotor_axis.set_ylabel(r"$\sin(\theta)$")
    _enable_grid(rotor_axis)
    _fixed_legend(rotor_axis, "lower left")

    voltage_a_line, = voltage_axis.plot([], [], label="Phase A voltage")
    voltage_b_line, = voltage_axis.plot([], [], label="Phase B voltage")
    voltage_c_line, = voltage_axis.plot([], [], label="Phase C voltage")
    current_a_line, = current_axis.plot([], [], label="Phase A current")
    current_b_line, = current_axis.plot([], [], label="Phase B current")
    current_c_line, = current_axis.plot([], [], label="Phase C current")
    voltage_axis.axvline(0.0, linestyle="--", label="_Current time")
    current_axis.axvline(0.0, linestyle="--", label="_Current time")

    voltage_peak = math.sqrt(2.0) * float(np.max(results.terminal_voltage_phase_rms))
    current_peak = math.sqrt(2.0) * float(np.max(results.load_current_phase_rms))
    voltage_axis.set_ylim(-1.15 * voltage_peak, 1.15 * voltage_peak)
    current_axis.set_ylim(-1.15 * current_peak, 1.15 * current_peak)
    current_axis.set_xlim(-half_window_s, half_window_s)
    voltage_axis.set_ylabel("Voltage (V)")
    current_axis.set_ylabel("Current (A)")
    current_axis.set_xlabel("Time relative to animated instant (s)")
    voltage_axis.set_title("Three-Phase Voltage")
    current_axis.set_title("Three-Phase Current")
    _enable_grid(voltage_axis)
    _enable_grid(current_axis)
    _fixed_legend(voltage_axis, "upper right")
    _fixed_legend(current_axis, "upper right")

    def update(frame_index: int) -> list[object]:
        current_time_s = active_frame_times_s[frame_index]
        sample_times_s = np.clip(
            current_time_s + relative_time_s,
            0.0,
            config.SIMULATION_TIME_S,
        )
        state_matrix = results.state_sampler(sample_times_s)
        omega_pu = state_matrix[0]
        theta_rad = state_matrix[3]
        field_current_pu = state_matrix[4]
        resistance_ohm = np.asarray(simulation.load.resistance_at(sample_times_s), dtype=float)
        terminal_quantities = simulation.electrical_model.terminal_quantities_at(
            resistance_ohm,
            field_current_pu,
            omega_pu,
        )
        voltage_a_v, voltage_b_v, voltage_c_v = simulation.model.three_phase_voltages(
            theta_rad,
            terminal_quantities["terminal_voltage_phase_rms"],
            terminal_quantities["terminal_voltage_angle_rad"],
        )
        current_a_a, current_b_a, current_c_a = simulation.model.phase_currents(
            voltage_a_v,
            voltage_b_v,
            voltage_c_v,
            resistance_ohm,
        )

        current_rotor_theta_rad = float(rotor_angle_rad[frame_index])
        current_reference_theta_rad = float(reference_angle_rad[frame_index])
        reference_x_values, reference_y_values = calculate_rotating_reference_vector(
            np.array([current_reference_theta_rad], dtype=float),
            radius=1.1,
        )
        electrical_reference_line.set_data(reference_x_values[0], reference_y_values[0])
        rotor_line.set_data(
            [0.0, 0.78 * math.cos(current_rotor_theta_rad)],
            [0.0, 0.78 * math.sin(current_rotor_theta_rad)],
        )
        voltage_a_line.set_data(relative_time_s, voltage_a_v)
        voltage_b_line.set_data(relative_time_s, voltage_b_v)
        voltage_c_line.set_data(relative_time_s, voltage_c_v)
        current_a_line.set_data(relative_time_s, current_a_a)
        current_b_line.set_data(relative_time_s, current_b_a)
        current_c_line.set_data(relative_time_s, current_c_a)
        return [
            electrical_reference_line,
            rotor_line,
            voltage_a_line,
            voltage_b_line,
            voltage_c_line,
            current_a_line,
            current_b_line,
            current_c_line,
        ]

    animation = FuncAnimation(
        figure,
        update,
        frames=len(active_frame_times_s),
        interval=1000.0 / config.ANIMATION_FPS,
        blit=False,
    )
    figure.tight_layout()
    return _save_animation(
        animation,
        output_dir / "02_rotor_three_phase_waveforms.gif",
        config,
        config.ROTOR_ANIMATION_FPS,
    )


def generate_governor_state_animation(
    results: SimulationResults,
    output_dir: Path,
    frame_times_s: FloatArray | None = None,
) -> Path:
    """Animate PI governor states or unregulated power imbalance."""
    config = results.config
    is_pi_controlled = config.CONTROL_MODE == "pi"
    active_frame_times_s = (
        frame_times_s if frame_times_s is not None else build_animation_frame_times(config)
    )
    frame_error_hz = _interpolate(results.frequency_error_hz, results.time_s, active_frame_times_s)
    if is_pi_controlled:
        frame_middle_quantity = _interpolate(results.integral_state, results.time_s, active_frame_times_s)
        middle_label = "PI integral state"
        middle_ylabel = "Integral state (pu*s)"
        title = "PI Governor Action"
        file_name = "03_pi_governor_states.gif"
    else:
        power_imbalance_pu = results.mechanical_power_pu - results.electrical_power_pu
        frame_middle_quantity = _interpolate(power_imbalance_pu, results.time_s, active_frame_times_s)
        middle_label = "Power imbalance Pm - Pe"
        middle_ylabel = "Power imbalance (pu)"
        title = "Unregulated Generator Power Imbalance"
        file_name = "03_unregulated_power_imbalance.gif"
    frame_reference_power_pu = _interpolate(
        results.mechanical_power_reference_pu,
        results.time_s,
        active_frame_times_s,
    )
    frame_electrical_power_pu = _interpolate(
        results.electrical_power_pu,
        results.time_s,
        active_frame_times_s,
    )
    frame_mechanical_power_pu = _interpolate(
        results.mechanical_power_pu,
        results.time_s,
        active_frame_times_s,
    )

    figure, axes = plt.subplots(3, 1, figsize=(9.5, 7.0), sharex=True)
    error_axis, integral_axis, power_axis = axes

    error_line, = error_axis.plot([], [], label="Frequency error")
    integral_line, = integral_axis.plot([], [], label=middle_label)
    reference_line, = power_axis.plot([], [], label="Mechanical power command")
    mechanical_line, = power_axis.plot([], [], label="Mechanical power")
    electrical_line, = power_axis.plot([], [], label="Electrical power")

    markers = [
        error_axis.axvline(0.0, linestyle="--", label="_Current time"),
        integral_axis.axvline(0.0, linestyle="--", label="_Current time"),
        power_axis.axvline(0.0, linestyle="--", label="_Current time"),
    ]
    for axis in axes:
        _add_load_step_markers(axis, config)
        _enable_grid(axis)
    _fixed_legend(error_axis, "upper right")
    _fixed_legend(integral_axis, "upper right")
    _fixed_legend(power_axis, "upper right")

    error_axis.axhline(0.0, linestyle=":", label="Zero error")
    error_axis.set_title(title)
    error_axis.set_ylabel("Error (Hz)")
    integral_axis.set_ylabel(middle_ylabel)
    power_axis.set_ylabel("Power (pu)")
    power_axis.set_xlabel("Time (s)")
    error_axis.set_ylim(*_axis_limits(results.frequency_error_hz))
    middle_axis_values = results.integral_state if is_pi_controlled else results.mechanical_power_pu - results.electrical_power_pu
    integral_axis.set_ylim(*_axis_limits(middle_axis_values))
    power_axis.set_ylim(
        *_axis_limits(
            np.concatenate(
                [
                    results.mechanical_power_reference_pu,
                    results.mechanical_power_pu,
                    results.electrical_power_pu,
                ]
            )
        )
    )
    power_axis.set_xlim(0.0, config.SIMULATION_TIME_S)

    def update(frame_index: int) -> list[object]:
        current_time_s = active_frame_times_s[frame_index]
        current_slice = slice(0, frame_index + 1)
        error_line.set_data(active_frame_times_s[current_slice], frame_error_hz[current_slice])
        integral_line.set_data(active_frame_times_s[current_slice], frame_middle_quantity[current_slice])
        reference_line.set_data(active_frame_times_s[current_slice], frame_reference_power_pu[current_slice])
        mechanical_line.set_data(active_frame_times_s[current_slice], frame_mechanical_power_pu[current_slice])
        electrical_line.set_data(active_frame_times_s[current_slice], frame_electrical_power_pu[current_slice])
        for marker in markers:
            marker.set_xdata([current_time_s, current_time_s])
        return [error_line, integral_line, reference_line, mechanical_line, electrical_line, *markers]

    animation = FuncAnimation(
        figure,
        update,
        frames=len(active_frame_times_s),
        interval=1000.0 / config.ANIMATION_FPS,
        blit=False,
    )
    figure.tight_layout()
    return _save_animation(animation, output_dir / file_name, config)


def generate_damping_comparison_animation(
    comparison: DampingComparison,
    output_dir: Path,
    frame_times_s: FloatArray | None = None,
) -> Path:
    """Animate the frequency and accelerating-power contrast between D=0 and D>0."""
    config = comparison.damped_results.config
    table = comparison.table
    active_frame_times_s = (
        frame_times_s if frame_times_s is not None else build_animation_frame_times(config)
    )
    frame_frequency_no_damping_hz = _interpolate(
        table["frequency_no_damping_hz"].to_numpy(dtype=float),
        table["time_s"].to_numpy(dtype=float),
        active_frame_times_s,
    )
    frame_frequency_with_damping_hz = _interpolate(
        table["frequency_with_damping_hz"].to_numpy(dtype=float),
        table["time_s"].to_numpy(dtype=float),
        active_frame_times_s,
    )
    frame_accelerating_power_no_damping_pu = _interpolate(
        table["accelerating_power_no_damping_pu"].to_numpy(dtype=float),
        table["time_s"].to_numpy(dtype=float),
        active_frame_times_s,
    )
    frame_accelerating_power_with_damping_pu = _interpolate(
        table["accelerating_power_with_damping_pu"].to_numpy(dtype=float),
        table["time_s"].to_numpy(dtype=float),
        active_frame_times_s,
    )

    figure, axes = plt.subplots(2, 1, figsize=(9.5, 6.2), sharex=True)
    frequency_axis, power_axis = axes

    frequency_axis.plot(
        table["time_s"],
        table["frequency_no_damping_hz"],
        alpha=0.20,
        label="_Full frequency, D = 0",
    )
    frequency_axis.plot(
        table["time_s"],
        table["frequency_with_damping_hz"],
        alpha=0.20,
        label=f"_Full frequency, D = {config.D:.2f}",
    )
    power_axis.plot(
        table["time_s"],
        table["accelerating_power_no_damping_pu"],
        alpha=0.20,
        label="_Full accelerating power, D = 0",
    )
    power_axis.plot(
        table["time_s"],
        table["accelerating_power_with_damping_pu"],
        alpha=0.20,
        label=f"_Full accelerating power, D = {config.D:.2f}",
    )

    no_damping_frequency_line, = frequency_axis.plot([], [], label="Animated frequency, D = 0")
    damped_frequency_line, = frequency_axis.plot(
        [],
        [],
        label=f"Animated frequency, D = {config.D:.2f}",
    )
    no_damping_power_line, = power_axis.plot([], [], label="Animated net power, D = 0")
    damped_power_line, = power_axis.plot(
        [],
        [],
        label=f"Animated net power, D = {config.D:.2f}",
    )

    frequency_marker = frequency_axis.axvline(0.0, linestyle="--", label="_Current time")
    power_marker = power_axis.axvline(0.0, linestyle="--", label="_Current time")
    frequency_axis.axhline(config.F_NOM_HZ, linestyle="--", label="Nominal frequency")
    frequency_axis.axhline(
        comparison.theory.final_frequency_hz,
        linestyle="-.",
        label=f"Expected damped final frequency = {comparison.theory.final_frequency_hz:.2f} Hz",
    )
    power_axis.axhline(0.0, linestyle=":", label="Zero acceleration")
    for axis in axes:
        _add_load_step_markers(axis, config)
        _enable_grid(axis)
    _fixed_legend(frequency_axis, "upper right")
    _fixed_legend(power_axis, "upper right")

    frequency_axis.set_title("Unregulated Generator: Speed-Coupled Voltage Creates Open-Loop Equilibria")
    frequency_axis.set_ylabel("Frequency (Hz)")
    power_axis.set_ylabel("Net accelerating power (pu)")
    power_axis.set_xlabel("Time (s)")
    frequency_axis.set_ylim(
        *_axis_limits(
            np.concatenate(
                [
                    table["frequency_no_damping_hz"].to_numpy(dtype=float),
                    table["frequency_with_damping_hz"].to_numpy(dtype=float),
                    np.array([comparison.theory.final_frequency_hz], dtype=float),
                ]
            )
        )
    )
    power_axis.set_ylim(
        *_axis_limits(
            np.concatenate(
                [
                    table["accelerating_power_no_damping_pu"].to_numpy(dtype=float),
                    table["accelerating_power_with_damping_pu"].to_numpy(dtype=float),
                ]
            )
        )
    )
    power_axis.set_xlim(0.0, config.SIMULATION_TIME_S)

    def update(frame_index: int) -> list[object]:
        current_time_s = active_frame_times_s[frame_index]
        current_slice = slice(0, frame_index + 1)
        no_damping_frequency_line.set_data(
            active_frame_times_s[current_slice],
            frame_frequency_no_damping_hz[current_slice],
        )
        damped_frequency_line.set_data(
            active_frame_times_s[current_slice],
            frame_frequency_with_damping_hz[current_slice],
        )
        no_damping_power_line.set_data(
            active_frame_times_s[current_slice],
            frame_accelerating_power_no_damping_pu[current_slice],
        )
        damped_power_line.set_data(
            active_frame_times_s[current_slice],
            frame_accelerating_power_with_damping_pu[current_slice],
        )
        for marker in [frequency_marker, power_marker]:
            marker.set_xdata([current_time_s, current_time_s])
        return [
            no_damping_frequency_line,
            damped_frequency_line,
            no_damping_power_line,
            damped_power_line,
            frequency_marker,
            power_marker,
        ]

    animation = FuncAnimation(
        figure,
        update,
        frames=len(active_frame_times_s),
        interval=1000.0 / config.ANIMATION_FPS,
        blit=False,
    )
    figure.tight_layout()
    return _save_animation(
        animation,
        output_dir / "04_unregulated_damping_comparison.gif",
        config,
    )


def generate_open_loop_voltage_animation(
    results: SimulationResults,
    output_dir: Path,
    frame_times_s: FloatArray | None = None,
) -> Path:
    """Animate open-loop frequency, terminal voltage, power, and field current."""
    config = results.config
    active_frame_times_s = (
        frame_times_s if frame_times_s is not None else build_animation_frame_times(config)
    )
    frame_frequency_hz = _interpolate(results.frequency_hz, results.time_s, active_frame_times_s)
    frame_terminal_voltage_v = _interpolate(
        results.terminal_voltage_ll_rms,
        results.time_s,
        active_frame_times_s,
    )
    frame_mechanical_power_pu = _interpolate(
        results.mechanical_power_pu,
        results.time_s,
        active_frame_times_s,
    )
    frame_electrical_power_pu = _interpolate(
        results.electrical_power_pu,
        results.time_s,
        active_frame_times_s,
    )
    frame_field_current_pu = _interpolate(results.field_current_pu, results.time_s, active_frame_times_s)

    figure, axes = plt.subplots(4, 1, figsize=(9.5, 8.0), sharex=True)
    frequency_axis, voltage_axis, power_axis, field_axis = axes

    frequency_line, = frequency_axis.plot([], [], label="Frequency")
    voltage_line, = voltage_axis.plot([], [], label="Terminal voltage")
    mechanical_line, = power_axis.plot([], [], label="Mechanical power")
    electrical_line, = power_axis.plot([], [], label="Electrical power")
    field_line, = field_axis.plot([], [], label="Field current")

    markers = [
        frequency_axis.axvline(0.0, linestyle="--", label="_Current time"),
        voltage_axis.axvline(0.0, linestyle="--", label="_Current time"),
        power_axis.axvline(0.0, linestyle="--", label="_Current time"),
        field_axis.axvline(0.0, linestyle="--", label="_Current time"),
    ]
    frequency_axis.axhline(config.F_NOM_HZ, linestyle="--", label="Nominal frequency")
    voltage_axis.axhline(config.V_LL_RMS, linestyle="--", label="Nominal voltage")
    for axis in axes:
        _add_load_step_markers(axis, config)
        _enable_grid(axis)
    _fixed_legend(frequency_axis, "upper right")
    _fixed_legend(voltage_axis, "upper right")
    _fixed_legend(power_axis, "upper right")
    _fixed_legend(field_axis, "upper right")

    frequency_axis.set_title("Open-Loop Speed and Voltage Response")
    frequency_axis.set_ylabel("Frequency (Hz)")
    voltage_axis.set_ylabel("Voltage (V LL RMS)")
    power_axis.set_ylabel("Power (pu)")
    field_axis.set_ylabel("Field current (pu)")
    field_axis.set_xlabel("Time (s)")
    frequency_axis.set_ylim(*_axis_limits(results.frequency_hz))
    voltage_axis.set_ylim(*_axis_limits(results.terminal_voltage_ll_rms))
    power_axis.set_ylim(*_axis_limits(np.concatenate([results.mechanical_power_pu, results.electrical_power_pu])))
    field_axis.set_ylim(*_axis_limits(results.field_current_pu))
    field_axis.set_xlim(0.0, config.SIMULATION_TIME_S)

    def update(frame_index: int) -> list[object]:
        current_time_s = active_frame_times_s[frame_index]
        current_slice = slice(0, frame_index + 1)
        frequency_line.set_data(active_frame_times_s[current_slice], frame_frequency_hz[current_slice])
        voltage_line.set_data(active_frame_times_s[current_slice], frame_terminal_voltage_v[current_slice])
        mechanical_line.set_data(active_frame_times_s[current_slice], frame_mechanical_power_pu[current_slice])
        electrical_line.set_data(active_frame_times_s[current_slice], frame_electrical_power_pu[current_slice])
        field_line.set_data(active_frame_times_s[current_slice], frame_field_current_pu[current_slice])
        for marker in markers:
            marker.set_xdata([current_time_s, current_time_s])
        return [frequency_line, voltage_line, mechanical_line, electrical_line, field_line, *markers]

    animation = FuncAnimation(
        figure,
        update,
        frames=len(active_frame_times_s),
        interval=1000.0 / config.ANIMATION_FPS,
        blit=False,
    )
    figure.tight_layout()
    return _save_animation(
        animation,
        output_dir / "05_open_loop_voltage_frequency.gif",
        config,
    )


def generate_rotor_reference_slip_animation(
    results: SimulationResults,
    output_dir: Path,
    frame_times_s: FloatArray | None = None,
) -> Path:
    """Animate rotor-reference slip with synchronized electrical quantities."""
    config = results.config
    active_frame_times_s = (
        frame_times_s if frame_times_s is not None else build_slip_animation_frame_times(config)
    )
    animation_time_s = active_frame_times_s
    frame_frequency_hz = _interpolate(results.frequency_hz, results.time_s, active_frame_times_s)
    frame_terminal_voltage_v = _interpolate(
        results.terminal_voltage_ll_rms,
        results.time_s,
        active_frame_times_s,
    )
    frame_internal_voltage_v = _interpolate(
        results.internal_voltage_ll_rms,
        results.time_s,
        active_frame_times_s,
    )
    frame_mechanical_power_pu = _interpolate(
        results.mechanical_power_pu,
        results.time_s,
        active_frame_times_s,
    )
    frame_electrical_power_pu = _interpolate(
        results.electrical_power_pu,
        results.time_s,
        active_frame_times_s,
    )
    frame_load_resistance_ohm = _interpolate(
        results.load_resistance_ohm,
        results.time_s,
        active_frame_times_s,
    )
    frame_terminal_angle_rad = _interpolate(
        results.terminal_voltage_angle_rad,
        results.time_s,
        active_frame_times_s,
    )
    frame_internal_voltage_pu = frame_internal_voltage_v / config.V_LL_RMS
    frame_terminal_voltage_pu = frame_terminal_voltage_v / config.V_LL_RMS
    base_current_a = config.S_BASE_VA / (math.sqrt(3.0) * config.V_LL_RMS)
    frame_load_current_pu = (
        _interpolate(results.load_current_phase_rms, results.time_s, active_frame_times_s)
        / base_current_a
    )
    reference_angle_rad, rotor_angle_rad, lead_cycles = calculate_slow_motion_display_angles(
        results,
        active_frame_times_s,
    )

    figure = plt.figure(figsize=(13.2, 10.2))
    grid = figure.add_gridspec(
        4,
        3,
        width_ratios=[1.15, 1.35, 1.35],
        height_ratios=[1.0, 1.0, 0.90, 0.95],
    )
    rotor_axis = figure.add_subplot(grid[0:2, 0])
    phasor_axis = figure.add_subplot(grid[2:, 0])
    frequency_axis = figure.add_subplot(grid[0, 1])
    voltage_axis = figure.add_subplot(grid[0, 2], sharex=frequency_axis)
    power_axis = figure.add_subplot(grid[1, 1], sharex=frequency_axis)
    internal_voltage_axis = figure.add_subplot(grid[1, 2], sharex=frequency_axis)
    resistance_axis = figure.add_subplot(grid[2, 1:], sharex=frequency_axis)
    lead_axis = figure.add_subplot(grid[3, 1:], sharex=frequency_axis)

    angle = np.linspace(0.0, 2.0 * math.pi, 400, dtype=float)
    rotor_axis.plot(np.cos(angle), np.sin(angle), label="_Reference circle")
    rotor_axis.axhline(0.0, linewidth=0.8)
    rotor_axis.axvline(0.0, linewidth=0.8)
    sector_x_values, sector_y_values = calculate_lag_sector_points(0.0, 0.0)
    lag_sector = Polygon(
        np.column_stack([sector_x_values, sector_y_values]),
        closed=True,
        facecolor="tab:orange",
        alpha=calculate_lag_sector_alpha(0.0),
        edgecolor="none",
        label="_Lag sector",
        zorder=1,
    )
    rotor_axis.add_patch(lag_sector)
    reference_line, = rotor_axis.plot(
        [],
        [],
        linestyle="--",
        linewidth=2.0,
        label=f"{config.F_NOM_HZ:.0f} Hz reference",
        zorder=3,
    )
    rotor_line, = rotor_axis.plot([], [], marker="o", linewidth=2.0, label="Rotor angle", zorder=4)
    lead_text = rotor_axis.text(
        0.04,
        0.95,
        "",
        transform=rotor_axis.transAxes,
        va="top",
        fontsize=10,
    )
    rotor_axis.set_aspect("equal", adjustable="box")
    rotor_axis.set_xlim(-1.2, 1.2)
    rotor_axis.set_ylim(-1.2, 1.2)
    rotor_axis.set_title("Slow-Motion Rotor Lag")
    rotor_axis.set_xlabel(r"$\cos(\theta)$")
    rotor_axis.set_ylabel(r"$\sin(\theta)$")
    _enable_grid(rotor_axis)
    _fixed_legend(rotor_axis, "lower left")

    phasor_axis.axhline(0.0, linewidth=0.8)
    phasor_axis.axvline(0.0, linewidth=0.8)
    phasor_reference_line, = phasor_axis.plot(
        [0.0, 1.0],
        [0.0, 0.0],
        linestyle="--",
        linewidth=1.4,
        label="_Internal voltage reference",
    )
    internal_voltage_phasor_line, = phasor_axis.plot([], [], marker="o", label="Internal E")
    terminal_voltage_phasor_line, = phasor_axis.plot([], [], marker="o", label="Terminal V")
    load_current_phasor_line, = phasor_axis.plot([], [], marker="o", label="Load I")
    internal_voltage_text = phasor_axis.text(0.0, 0.0, "E", fontsize=9)
    terminal_voltage_text = phasor_axis.text(0.0, 0.0, "V", fontsize=9)
    load_current_text = phasor_axis.text(0.0, 0.0, "I", fontsize=9)
    phasor_limit = 1.20 * float(
        np.max(
            np.concatenate(
                [
                    frame_internal_voltage_pu,
                    frame_terminal_voltage_pu,
                    frame_load_current_pu,
                ]
            )
        )
    )
    phasor_axis.set_aspect("equal", adjustable="box")
    phasor_axis.set_xlim(-phasor_limit, phasor_limit)
    phasor_axis.set_ylim(-phasor_limit, phasor_limit)
    phasor_axis.set_title("Terminal Phasors")
    phasor_axis.set_xlabel("Real axis (pu)")
    phasor_axis.set_ylabel("Imaginary axis (pu)")
    _enable_grid(phasor_axis)
    _fixed_legend(phasor_axis, "lower left")

    frequency_axis.plot(
        animation_time_s,
        frame_frequency_hz,
        alpha=0.25,
        label="_Full frequency",
    )
    frequency_line, = frequency_axis.plot([], [], label="Frequency")
    frequency_axis.axhline(config.F_NOM_HZ, linestyle="--", label="Nominal frequency")
    frequency_axis.set_title("Frequency")
    frequency_axis.set_ylabel("Frequency (Hz)")
    _enable_grid(frequency_axis)
    _fixed_legend(frequency_axis, "upper right")

    voltage_axis.plot(
        animation_time_s,
        frame_terminal_voltage_v,
        alpha=0.25,
        label="_Full terminal voltage",
    )
    voltage_line, = voltage_axis.plot([], [], label="Terminal voltage")
    voltage_axis.axhline(config.V_LL_RMS, linestyle="--", label="Nominal voltage")
    voltage_axis.set_title("Terminal Voltage")
    voltage_axis.set_ylabel("Voltage (V LL RMS)")
    _enable_grid(voltage_axis)
    _fixed_legend(voltage_axis, "upper right")

    power_axis.plot(
        animation_time_s,
        frame_mechanical_power_pu,
        alpha=0.25,
        label="_Full mechanical power",
    )
    power_axis.plot(
        animation_time_s,
        frame_electrical_power_pu,
        alpha=0.25,
        label="_Full electrical power",
    )
    mechanical_power_line, = power_axis.plot([], [], label="Mechanical power")
    electrical_power_line, = power_axis.plot([], [], label="Electrical power")
    power_axis.set_title("Power Balance")
    power_axis.set_ylabel("Power (pu)")
    _enable_grid(power_axis)
    _fixed_legend(power_axis, "upper right")

    internal_voltage_axis.plot(
        animation_time_s,
        frame_internal_voltage_v,
        alpha=0.25,
        label="_Full internal voltage",
    )
    internal_voltage_line, = internal_voltage_axis.plot([], [], label="Internal voltage")
    internal_voltage_axis.set_title("Internal Voltage")
    internal_voltage_axis.set_ylabel("Voltage (V LL RMS)")
    _enable_grid(internal_voltage_axis)
    _fixed_legend(internal_voltage_axis, "upper right")

    resistance_axis.plot(
        animation_time_s,
        frame_load_resistance_ohm,
        alpha=0.25,
        label="_Full load resistance",
    )
    resistance_line, = resistance_axis.plot([], [], label="Load resistance")
    resistance_axis.set_title("Load Resistance")
    resistance_axis.set_ylabel("Resistance (ohm)")
    _enable_grid(resistance_axis)
    _fixed_legend(resistance_axis, "upper right")

    lead_axis.plot(
        animation_time_s,
        lead_cycles,
        alpha=0.25,
        label="_Full reference lead",
    )
    lead_line, = lead_axis.plot([], [], label="Reference lead")
    lead_axis.axhline(0.0, linestyle="--", label="Zero lag")
    lead_axis.set_title("Accumulated Rotor Lag")
    lead_axis.set_ylabel("Lead (slow-motion cycles)")
    lead_axis.set_xlabel("Simulation time (s)")
    _enable_grid(lead_axis)
    _fixed_legend(lead_axis, "upper left")

    chart_axes = [
        frequency_axis,
        voltage_axis,
        power_axis,
        internal_voltage_axis,
        resistance_axis,
        lead_axis,
    ]
    current_markers = [
        axis.axvline(0.0, linestyle="--", label="_Current time")
        for axis in chart_axes
    ]
    for axis in chart_axes:
        _add_load_step_markers(axis, config)
        axis.set_xlim(animation_time_s[0], animation_time_s[-1])
    _fixed_legend(frequency_axis, "upper right")
    _fixed_legend(voltage_axis, "upper right")
    _fixed_legend(power_axis, "upper right")
    _fixed_legend(internal_voltage_axis, "upper right")
    _fixed_legend(lead_axis, "upper left")

    frequency_axis.set_ylim(*_axis_limits(np.concatenate([frame_frequency_hz, np.array([config.F_NOM_HZ])])))
    voltage_axis.set_ylim(*_axis_limits(np.concatenate([frame_terminal_voltage_v, np.array([config.V_LL_RMS])])))
    power_axis.set_ylim(
        *_axis_limits(
            np.concatenate(
                [
                    frame_mechanical_power_pu,
                    frame_electrical_power_pu,
                ]
            )
        )
    )
    internal_voltage_axis.set_ylim(*_axis_limits(frame_internal_voltage_v))
    resistance_axis.set_ylim(*_axis_limits(frame_load_resistance_ohm))
    lead_axis.set_ylim(*_axis_limits(lead_cycles))

    def update(frame_index: int) -> list[object]:
        current_slice = slice(0, frame_index + 1)
        current_time_s = animation_time_s[frame_index]
        current_reference_angle_rad = float(reference_angle_rad[frame_index])
        current_rotor_angle_rad = float(rotor_angle_rad[frame_index])
        current_sector_x_values, current_sector_y_values = calculate_lag_sector_points(
            current_reference_angle_rad,
            current_rotor_angle_rad,
        )
        lag_sector.set_xy(np.column_stack([current_sector_x_values, current_sector_y_values]))
        lag_sector.set_alpha(calculate_lag_sector_alpha(float(lead_cycles[frame_index])))

        reference_line.set_data(
            [0.0, 1.08 * math.cos(current_reference_angle_rad)],
            [0.0, 1.08 * math.sin(current_reference_angle_rad)],
        )
        rotor_line.set_data(
            [0.0, 0.82 * math.cos(current_rotor_angle_rad)],
            [0.0, 0.82 * math.sin(current_rotor_angle_rad)],
        )
        current_internal_voltage_pu = float(frame_internal_voltage_pu[frame_index])
        current_terminal_voltage_pu = float(frame_terminal_voltage_pu[frame_index])
        current_load_current_pu = float(frame_load_current_pu[frame_index])
        current_terminal_angle_rad = float(frame_terminal_angle_rad[frame_index])
        internal_voltage_x = current_internal_voltage_pu
        internal_voltage_y = 0.0
        terminal_voltage_x = current_terminal_voltage_pu * math.cos(current_terminal_angle_rad)
        terminal_voltage_y = current_terminal_voltage_pu * math.sin(current_terminal_angle_rad)
        load_current_x = current_load_current_pu * math.cos(current_terminal_angle_rad)
        load_current_y = current_load_current_pu * math.sin(current_terminal_angle_rad)
        phasor_reference_line.set_data([0.0, phasor_limit], [0.0, 0.0])
        internal_voltage_phasor_line.set_data([0.0, internal_voltage_x], [0.0, internal_voltage_y])
        terminal_voltage_phasor_line.set_data([0.0, terminal_voltage_x], [0.0, terminal_voltage_y])
        load_current_phasor_line.set_data([0.0, load_current_x], [0.0, load_current_y])
        internal_voltage_text.set_position((internal_voltage_x * 1.04, internal_voltage_y + 0.04))
        terminal_voltage_text.set_position((terminal_voltage_x * 1.04, terminal_voltage_y * 1.04))
        load_current_text.set_position((load_current_x * 1.04, load_current_y * 1.04 - 0.08))
        completed_turns = int(math.floor(abs(float(lead_cycles[frame_index]))))
        lead_text.set_text(
            f"Lead = {lead_cycles[frame_index]:+.2f} cycles\nFull turns = {completed_turns}"
        )
        frequency_line.set_data(
            animation_time_s[current_slice],
            frame_frequency_hz[current_slice],
        )
        voltage_line.set_data(
            animation_time_s[current_slice],
            frame_terminal_voltage_v[current_slice],
        )
        mechanical_power_line.set_data(
            animation_time_s[current_slice],
            frame_mechanical_power_pu[current_slice],
        )
        electrical_power_line.set_data(
            animation_time_s[current_slice],
            frame_electrical_power_pu[current_slice],
        )
        internal_voltage_line.set_data(
            animation_time_s[current_slice],
            frame_internal_voltage_v[current_slice],
        )
        resistance_line.set_data(
            animation_time_s[current_slice],
            frame_load_resistance_ohm[current_slice],
        )
        lead_line.set_data(
            animation_time_s[current_slice],
            lead_cycles[current_slice],
        )
        for marker in current_markers:
            marker.set_xdata([current_time_s, current_time_s])
        return [
            lag_sector,
            reference_line,
            rotor_line,
            lead_text,
            phasor_reference_line,
            internal_voltage_phasor_line,
            terminal_voltage_phasor_line,
            load_current_phasor_line,
            internal_voltage_text,
            terminal_voltage_text,
            load_current_text,
            frequency_line,
            voltage_line,
            mechanical_power_line,
            electrical_power_line,
            internal_voltage_line,
            resistance_line,
            lead_line,
            *current_markers,
        ]

    animation = FuncAnimation(
        figure,
        update,
        frames=len(active_frame_times_s),
        interval=1000.0 / config.SLIP_ANIMATION_FPS,
        blit=False,
    )
    figure.tight_layout()
    return _save_mp4_animation(
        animation,
        output_dir / "06_rotor_reference_slip.mp4",
        config,
        config.SLIP_ANIMATION_FPS,
    )


def generate_all_animations(
    simulation: DynamicSimulation,
    results: SimulationResults,
    output_dir: Path,
) -> list[Path]:
    """Generate all GIF animations for the selected generator case."""
    frame_times_s = build_animation_frame_times(results.config)
    rotor_frame_times_s = build_rotor_animation_frame_times(results.config)
    slip_frame_times_s = build_slip_animation_frame_times(results.config)
    animation_paths = [
        generate_frequency_power_animation(results, output_dir, frame_times_s),
        generate_rotor_waveform_animation(simulation, results, output_dir, rotor_frame_times_s),
        generate_governor_state_animation(results, output_dir, frame_times_s),
        generate_open_loop_voltage_animation(results, output_dir, frame_times_s),
        generate_rotor_reference_slip_animation(results, output_dir, slip_frame_times_s),
    ]
    return animation_paths
