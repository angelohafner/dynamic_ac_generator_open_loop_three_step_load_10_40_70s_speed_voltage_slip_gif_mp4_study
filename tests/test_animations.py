from types import SimpleNamespace
import inspect

import matplotlib.pyplot as plt
import numpy as np

from dynamic_ac_generator import animation
from dynamic_ac_generator.animation import (
    build_animation_frame_times,
    build_rotor_animation_frame_times,
    calculate_rotating_reference_vector,
    calculate_slow_motion_rotor_angle,
)
from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.simulation import DynamicSimulation


def _build_slower_rotor_results(config: SimulationConfig) -> SimpleNamespace:
    pre_step_time_s = getattr(config, "SLIP_ANIMATION_PRE_STEP_TIME_S", 1.0)
    return SimpleNamespace(
        config=config,
        time_s=np.array(
            [
                config.LOAD_STEP_TIME_S - pre_step_time_s,
                config.LOAD_STEP_TIME_S,
                config.SECOND_LOAD_STEP_TIME_S,
                config.SIMULATION_TIME_S,
            ],
            dtype=float,
        ),
        omega_pu=np.array([1.0, 1.0, 0.95, 1.0], dtype=float),
    )


def test_animation_frame_times_include_start_load_step_and_end() -> None:
    config = SimulationConfig()

    frame_times = build_animation_frame_times(config, frame_count=25)

    assert np.isclose(frame_times[0], 0.0)
    assert np.any(np.isclose(frame_times, config.LOAD_STEP_TIME_S))
    assert np.isclose(frame_times[-1], config.SIMULATION_TIME_S)
    assert np.all(np.diff(frame_times) > 0.0)


def test_rotor_animation_uses_denser_default_frame_times() -> None:
    config = SimulationConfig()

    slow_frame_times = build_animation_frame_times(config)
    rotor_frame_times = build_rotor_animation_frame_times(config)

    assert len(rotor_frame_times) > 2 * len(slow_frame_times)
    assert 0.0 < rotor_frame_times[0] < config.LOAD_STEP_TIME_S
    assert np.any(np.isclose(rotor_frame_times, config.LOAD_STEP_TIME_S))
    assert rotor_frame_times[-1] < config.SIMULATION_TIME_S


def test_rotor_animation_focuses_on_16_ms_around_load_step() -> None:
    config = SimulationConfig()

    rotor_frame_times = build_rotor_animation_frame_times(config)
    expected_start_s = config.LOAD_STEP_TIME_S - config.ROTOR_ANIMATION_PRE_STEP_TIME_S
    expected_end_s = config.LOAD_STEP_TIME_S + config.ROTOR_ANIMATION_POST_STEP_TIME_S

    assert np.isclose(rotor_frame_times[0], expected_start_s)
    assert np.isclose(rotor_frame_times[-1], expected_end_s)
    assert np.isclose(
        rotor_frame_times[-1] - rotor_frame_times[0],
        0.032,
    )
    assert np.isclose(config.ROTOR_ANIMATION_PRE_STEP_TIME_S, 0.016)
    assert np.isclose(config.ROTOR_ANIMATION_POST_STEP_TIME_S, 0.016)
    assert config.ROTOR_ANIMATION_FPS < config.ANIMATION_FPS


def test_slow_motion_rotor_angle_limits_visual_step_size() -> None:
    config = SimulationConfig()
    results = DynamicSimulation(config).run()
    frame_times = build_rotor_animation_frame_times(config)

    display_angle_rad = calculate_slow_motion_rotor_angle(results, frame_times)
    maximum_step_degrees = np.rad2deg(np.max(np.abs(np.diff(display_angle_rad))))

    assert maximum_step_degrees <= 20.0


def test_rotating_reference_vector_changes_direction() -> None:
    x_values, y_values = calculate_rotating_reference_vector(
        np.array([0.0, np.pi / 2.0], dtype=float),
        radius=1.1,
    )

    assert np.allclose(x_values[0], np.array([0.0, 1.1]))
    assert np.allclose(y_values[0], np.array([0.0, 0.0]))
    assert np.allclose(x_values[1], np.array([0.0, 0.0]), atol=1e-12)
    assert np.allclose(y_values[1], np.array([0.0, 1.1]))


def test_synchronous_reference_is_independent_from_slowing_rotor() -> None:
    assert hasattr(animation, "build_slip_animation_frame_times")
    assert hasattr(animation, "calculate_synchronous_reference_angle")

    config = SimulationConfig()
    results = _build_slower_rotor_results(config)
    frame_times = animation.build_slip_animation_frame_times(config, frame_count=80)

    reference_angle_rad = animation.calculate_synchronous_reference_angle(config, frame_times)
    rotor_angle_rad = calculate_slow_motion_rotor_angle(results, frame_times)

    assert not np.allclose(reference_angle_rad, rotor_angle_rad)
    assert np.max(np.abs(reference_angle_rad - rotor_angle_rad)) > np.deg2rad(30.0)


def test_rotor_reference_lag_increases_when_rotor_is_below_nominal() -> None:
    assert hasattr(animation, "build_slip_animation_frame_times")
    assert hasattr(animation, "calculate_rotor_reference_lag")

    config = SimulationConfig()
    results = _build_slower_rotor_results(config)
    frame_times = animation.build_slip_animation_frame_times(config, frame_count=80)

    lag_rad = animation.calculate_rotor_reference_lag(results, frame_times)

    assert np.isclose(lag_rad[0], 0.0)
    assert np.all(np.diff(lag_rad[1:]) >= -1e-9)
    assert lag_rad[-1] > np.deg2rad(30.0)


def test_slip_animation_frame_times_include_pre_step_window() -> None:
    config = SimulationConfig()

    assert hasattr(config, "SLIP_ANIMATION_PRE_STEP_TIME_S")

    frame_times = animation.build_slip_animation_frame_times(config, frame_count=80)

    assert np.isclose(frame_times[0], config.LOAD_STEP_TIME_S - config.SLIP_ANIMATION_PRE_STEP_TIME_S)
    assert np.any(np.isclose(frame_times, config.LOAD_STEP_TIME_S))
    assert np.isclose(frame_times[-1], config.LOAD_STEP_TIME_S + config.SLIP_ANIMATION_DURATION_S)


def test_slip_animation_frame_times_reach_default_simulation_end() -> None:
    config = SimulationConfig()

    frame_times = animation.build_slip_animation_frame_times(config)

    assert np.isclose(
        config.SLIP_ANIMATION_DURATION_S,
        config.SIMULATION_TIME_S - config.LOAD_STEP_TIME_S,
    )
    assert np.isclose(frame_times[-1], config.SIMULATION_TIME_S)


def test_slow_motion_vectors_rotate_counterclockwise_and_lag_after_step() -> None:
    config = SimulationConfig()
    results = _build_slower_rotor_results(config)
    frame_times = animation.build_slip_animation_frame_times(config, frame_count=80)

    assert hasattr(config, "SLOW_MOTION_REFERENCE_FREQUENCY_HZ")
    assert hasattr(animation, "calculate_slow_motion_display_angles")

    reference_angle_rad, rotor_angle_rad, lead_cycles = animation.calculate_slow_motion_display_angles(
        results,
        frame_times,
    )
    pre_step_mask = frame_times <= config.LOAD_STEP_TIME_S
    post_step_mask = frame_times >= config.LOAD_STEP_TIME_S
    relative_angle_rad = reference_angle_rad - rotor_angle_rad

    assert np.all(np.diff(reference_angle_rad) > 0.0)
    assert np.all(np.diff(rotor_angle_rad) > 0.0)
    assert np.allclose(relative_angle_rad[pre_step_mask], relative_angle_rad[0], atol=1e-12)
    assert np.all(np.diff(relative_angle_rad[post_step_mask]) >= -1e-9)
    assert lead_cycles[-1] > lead_cycles[post_step_mask][0]


def test_slow_motion_slip_animation_uses_dense_smooth_playback() -> None:
    config = SimulationConfig()
    frame_times = animation.build_slip_animation_frame_times(config)
    reference_angle_rad = animation.calculate_slow_motion_reference_angle(config, frame_times)
    maximum_reference_step_degrees = np.rad2deg(np.max(np.abs(np.diff(reference_angle_rad))))

    assert np.isclose(config.SLOW_MOTION_REFERENCE_FREQUENCY_HZ, 0.40)
    assert config.SLIP_ANIMATION_FRAME_COUNT >= 1440
    assert config.SLIP_ANIMATION_FPS == 24
    assert maximum_reference_step_degrees < 10.0
    assert np.isclose(config.SIMULATION_TIME_S, 100.0)
    assert np.isclose(config.SLIP_ANIMATION_DURATION_S, 90.0)


def test_rotor_reference_slip_does_not_keep_gif_pair_helper() -> None:
    assert not hasattr(animation, "mp4_path_for_gif")


def test_animation_grid_uses_half_opacity() -> None:
    assert hasattr(animation, "_enable_grid")

    figure, axis = plt.subplots()
    animation._enable_grid(axis)
    figure.canvas.draw()

    visible_gridlines = [
        gridline
        for gridline in [*axis.get_xgridlines(), *axis.get_ygridlines()]
        if gridline.get_visible()
    ]

    assert visible_gridlines
    assert all(np.isclose(gridline.get_alpha(), 0.5) for gridline in visible_gridlines)
    plt.close(figure)


def test_load_step_markers_are_hidden_from_animation_legends() -> None:
    figure, axis = plt.subplots()
    animation._add_load_step_markers(axis, SimulationConfig())

    labels = [line.get_label() for line in axis.lines]

    assert labels
    assert all(label.startswith("_") for label in labels)
    plt.close(figure)


def test_rotor_reference_slip_auxiliary_labels_are_hidden() -> None:
    source = inspect.getsource(animation.generate_rotor_reference_slip_animation)

    forbidden_labels = [
        'label="Reference circle"',
        'label="Current time"',
        'label="Load step 1"',
        'label="Load step 2"',
        'label="Lag sector"',
        'label="Full frequency"',
        'label="Full mechanical power"',
        'label="Full electrical power"',
        'label="Full reference lead"',
    ]

    for forbidden_label in forbidden_labels:
        assert forbidden_label not in source


def test_rotor_reference_slip_uses_latex_axis_labels_and_dashed_references() -> None:
    source = inspect.getsource(animation.generate_rotor_reference_slip_animation)

    assert 'set_xlabel(r"$\\cos(\\theta)$")' in source
    assert 'set_ylabel(r"$\\sin(\\theta)$")' in source
    assert 'label="_Lag sector"' in source
    assert 'label="Nominal frequency"' in source
    assert 'label="Nominal voltage"' in source
    assert 'label="Zero lag"' in source
    assert 'linestyle="--", label="Nominal frequency"' in source
    assert 'linestyle="--", label="Nominal voltage"' in source
    assert 'linestyle="--", label="Zero lag"' in source
    assert '"06_rotor_reference_slip.mp4"' in source


def test_rotor_reference_slip_renders_mp4_without_gif_export() -> None:
    source = inspect.getsource(animation.generate_rotor_reference_slip_animation)

    assert '"06_rotor_reference_slip.mp4"' in source
    assert '"06_rotor_reference_slip.gif"' not in source
    assert "save_mp4=True" not in source


def test_rotor_reference_slip_includes_load_resistance_panel() -> None:
    source = inspect.getsource(animation.generate_rotor_reference_slip_animation)

    assert "frame_load_resistance_ohm" in source
    assert "Load Resistance" in source
    assert "Resistance (ohm)" in source
    assert "results.load_resistance_ohm" in source


def test_rotor_reference_slip_includes_phasor_panel_below_rotor() -> None:
    source = inspect.getsource(animation.generate_rotor_reference_slip_animation)

    assert "phasor_axis" in source
    assert "Terminal Phasors" in source
    assert "frame_terminal_angle_rad" in source
    assert "frame_load_current_pu" in source
    assert "load_current_phase_rms" in source


def test_rotor_reference_slip_uses_absolute_simulation_time_axis() -> None:
    source = inspect.getsource(animation.generate_rotor_reference_slip_animation)

    assert "relative_frame_times_s = active_frame_times_s - config.LOAD_STEP_TIME_S" not in source
    assert 'set_xlabel("Simulation time (s)")' in source


def test_lag_sector_alpha_starts_at_20_percent_and_increases_by_cycles() -> None:
    assert hasattr(animation, "calculate_lag_sector_alpha")

    zero_alpha = animation.calculate_lag_sector_alpha(0.0)
    one_turn_alpha = animation.calculate_lag_sector_alpha(1.0)
    many_turns_alpha = animation.calculate_lag_sector_alpha(100.0)
    negative_turn_alpha = animation.calculate_lag_sector_alpha(-2.0)

    assert np.isclose(zero_alpha, 0.20)
    assert one_turn_alpha > zero_alpha
    assert negative_turn_alpha > one_turn_alpha
    assert np.isclose(many_turns_alpha, 0.80)


def test_lag_sector_points_span_from_rotor_to_reference() -> None:
    assert hasattr(animation, "calculate_lag_sector_points")

    x_values, y_values = animation.calculate_lag_sector_points(
        reference_angle_rad=np.pi / 2.0,
        rotor_angle_rad=0.0,
        radius=0.75,
        sample_count=12,
    )

    assert np.allclose([x_values[0], y_values[0]], [0.0, 0.0])
    assert np.allclose([x_values[1], y_values[1]], [0.75, 0.0])
    assert np.allclose([x_values[-2], y_values[-2]], [0.0, 0.75], atol=1e-12)
    assert np.allclose([x_values[-1], y_values[-1]], [0.0, 0.0])
    assert len(x_values) == 14
    assert len(y_values) == 14


def test_animation_module_does_not_use_moving_best_legends() -> None:
    from dynamic_ac_generator import animation
    import inspect

    source = inspect.getsource(animation)

    assert 'loc="best"' not in source
