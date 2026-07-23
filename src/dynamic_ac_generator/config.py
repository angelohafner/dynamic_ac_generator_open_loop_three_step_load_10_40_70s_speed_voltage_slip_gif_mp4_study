"""Simulation configuration and derived base quantities."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SimulationConfig:
    """Configuration parameters for the isolated generator simulation."""

    CONTROL_MODE: str = "unregulated"

    F_NOM_HZ: float = 60.0
    V_LL_RMS: float = 400.0
    S_BASE_VA: float = 100_000.0
    FIELD_CURRENT_INITIAL_PU: float = 1.0
    STATOR_RESISTANCE_PU: float = 0.02
    SYNCHRONOUS_REACTANCE_PU: float = 0.50

    H: float = 3.0
    D: float = 0.0
    DAMPED_COMPARISON_D: float = 2.0
    DAMPING_COMPARISON_SIMULATION_TIME_S: float = 100.0
    DAMPING_SETTLING_TOLERANCE_HZ: float = 0.50

    KP: float = 5.0
    KI: float = 2.0
    T_M: float = 0.2

    P_M_MIN_PU: float = 0.0
    P_M_MAX_PU: float = 3.0

    INITIAL_LOAD_PU: float = 0.50
    INITIAL_LOAD_ANGLE_DEG: float = -45.0
    FINAL_LOAD_PU: float = 0.60
    FINAL_LOAD_ANGLE_DEG: float = -30.0
    SECOND_LOAD_STEP_TIME_S: float | None = 40.0
    SECOND_STEP_LOAD_PU: float | None = 0.60
    SECOND_STEP_LOAD_ANGLE_DEG: float | None = -60.0
    THIRD_LOAD_STEP_TIME_S: float | None = 70.0
    THIRD_STEP_LOAD_PU: float | None = 0.50
    THIRD_STEP_LOAD_ANGLE_DEG: float | None = -45.0
    ADDITIONAL_LOAD_STEPS: tuple[tuple[float, float, float], ...] | None = None

    LOAD_STEP_TIME_S: float = 10.0
    SIMULATION_TIME_S: float = 100.0
    FREQUENCY_TOLERANCE_HZ: float = 0.01

    DYNAMIC_SAMPLE_STEP_S: float = 0.001
    SLOW_MAX_STEP_S: float = 0.001
    WAVEFORM_SAMPLE_STEP_S: float = 0.00005
    WAVEFORM_WINDOW_S: float = 0.12

    ANIMATION_FRAME_COUNT: int = 90
    ANIMATION_FPS: int = 15
    ANIMATION_DPI: int = 110
    ANIMATION_WAVEFORM_WINDOW_S: float = 0.08
    ROTOR_ANIMATION_FRAME_COUNT: int = 240
    ROTOR_ANIMATION_FPS: int = 12
    ROTOR_DISPLAY_FREQUENCY_HZ: float = 60.0
    ROTOR_ANIMATION_PRE_STEP_TIME_S: float = 0.016
    ROTOR_ANIMATION_POST_STEP_TIME_S: float = 0.016
    SLOW_MOTION_REFERENCE_FREQUENCY_HZ: float = 0.40
    SLIP_ANIMATION_PRE_STEP_TIME_S: float = 1.0
    SLIP_ANIMATION_DURATION_S: float = 90.0
    SLIP_ANIMATION_FRAME_COUNT: int = 1440
    SLIP_ANIMATION_FPS: int = 24

    RELATIVE_TOLERANCE: float = 1e-9
    ABSOLUTE_TOLERANCE: float = 1e-11

    def __post_init__(self) -> None:
        """Validate configuration values with clear error messages."""
        if self.F_NOM_HZ <= 0.0:
            raise ValueError("Nominal frequency must be positive.")
        if self.CONTROL_MODE not in {"unregulated", "pi"}:
            raise ValueError("Control mode must be either 'unregulated' or 'pi'.")
        if self.V_LL_RMS <= 0.0:
            raise ValueError("Nominal line-to-line RMS voltage must be positive.")
        if self.S_BASE_VA <= 0.0:
            raise ValueError("Base apparent power must be positive.")
        if self.FIELD_CURRENT_INITIAL_PU <= 0.0:
            raise ValueError("Initial field current must be positive.")
        if self.STATOR_RESISTANCE_PU < 0.0:
            raise ValueError("Stator resistance cannot be negative.")
        if self.SYNCHRONOUS_REACTANCE_PU < 0.0:
            raise ValueError("Synchronous reactance cannot be negative.")
        if self.H <= 0.0:
            raise ValueError("Inertia constant H must be positive.")
        if self.D < 0.0:
            raise ValueError("Damping coefficient D cannot be negative.")
        if self.DAMPED_COMPARISON_D <= 0.0:
            raise ValueError("Damped comparison coefficient must be positive.")
        if self.DAMPING_COMPARISON_SIMULATION_TIME_S <= self.LOAD_STEP_TIME_S:
            raise ValueError("Damping comparison simulation time must be greater than the load-step time.")
        if self.DAMPING_SETTLING_TOLERANCE_HZ <= 0.0:
            raise ValueError("Damping settling tolerance must be positive.")
        if self.KP < 0.0:
            raise ValueError("Governor proportional gain KP cannot be negative.")
        if self.KI < 0.0:
            raise ValueError("Governor integral gain KI cannot be negative.")
        if self.T_M <= 0.0:
            raise ValueError("Prime-mover time constant T_M must be positive.")
        if self.P_M_MIN_PU >= self.P_M_MAX_PU:
            raise ValueError("Mechanical power minimum must be lower than maximum.")
        if self.INITIAL_LOAD_PU <= 0.0:
            raise ValueError("Initial load impedance magnitude must be positive.")
        if self.FINAL_LOAD_PU <= 0.0:
            raise ValueError("Final load impedance magnitude must be positive.")
        if self.SECOND_LOAD_STEP_TIME_S is None and self.SECOND_STEP_LOAD_PU is not None:
            raise ValueError("Second load impedance magnitude requires a second load-step time.")
        if self.SECOND_LOAD_STEP_TIME_S is not None and self.SECOND_STEP_LOAD_PU is None:
            raise ValueError("Second load-step time requires a second load impedance magnitude.")
        if self.SECOND_LOAD_STEP_TIME_S is not None and self.SECOND_STEP_LOAD_ANGLE_DEG is None:
            raise ValueError("Second load-step time requires a second load impedance angle.")
        if self.SECOND_STEP_LOAD_PU is not None and self.SECOND_STEP_LOAD_PU <= 0.0:
            raise ValueError("Second load impedance magnitude must be positive.")
        if self.THIRD_LOAD_STEP_TIME_S is None and self.THIRD_STEP_LOAD_PU is not None:
            raise ValueError("Third load impedance magnitude requires a third load-step time.")
        if self.THIRD_LOAD_STEP_TIME_S is not None and self.THIRD_STEP_LOAD_PU is None:
            raise ValueError("Third load-step time requires a third load impedance magnitude.")
        if self.THIRD_LOAD_STEP_TIME_S is not None and self.THIRD_STEP_LOAD_ANGLE_DEG is None:
            raise ValueError("Third load-step time requires a third load impedance angle.")
        if self.THIRD_STEP_LOAD_PU is not None and self.THIRD_STEP_LOAD_PU <= 0.0:
            raise ValueError("Third load impedance magnitude must be positive.")
        if not math.isfinite(self.INITIAL_LOAD_ANGLE_DEG):
            raise ValueError("Initial load impedance angle must be finite.")
        if not math.isfinite(self.FINAL_LOAD_ANGLE_DEG):
            raise ValueError("Final load impedance angle must be finite.")
        initial_active_power_pu = self.nominal_voltage_active_power_pu(
            self.INITIAL_LOAD_PU,
            self.INITIAL_LOAD_ANGLE_DEG,
        )
        if not (self.P_M_MIN_PU <= initial_active_power_pu <= self.P_M_MAX_PU):
            raise ValueError("Initial active power must be inside the mechanical power limits.")
        if not (0.0 < self.LOAD_STEP_TIME_S < self.SIMULATION_TIME_S):
            raise ValueError("Load step time must be greater than zero and lower than the simulation time.")
        previous_step_time_s = self.LOAD_STEP_TIME_S
        for step_time_s, load_impedance_pu, load_angle_deg in self.additional_load_steps:
            if load_impedance_pu <= 0.0:
                raise ValueError("Additional load impedance magnitudes must be positive.")
            if not math.isfinite(load_angle_deg):
                raise ValueError("Additional load impedance angles must be finite.")
            if not (previous_step_time_s < step_time_s < self.SIMULATION_TIME_S):
                raise ValueError("Additional load-step times must be increasing and inside the simulation time.")
            previous_step_time_s = step_time_s
        if self.DAMPING_COMPARISON_SIMULATION_TIME_S <= previous_step_time_s:
            raise ValueError("Damping comparison simulation time must cover every load-step time.")
        if self.FREQUENCY_TOLERANCE_HZ <= 0.0:
            raise ValueError("Frequency tolerance must be positive.")
        if self.DYNAMIC_SAMPLE_STEP_S <= 0.0:
            raise ValueError("Dynamic sample step must be positive.")
        if self.SLOW_MAX_STEP_S <= 0.0:
            raise ValueError("Maximum ODE step must be positive.")
        if self.WAVEFORM_SAMPLE_STEP_S <= 0.0:
            raise ValueError("Waveform sample step must be positive.")
        if self.WAVEFORM_WINDOW_S <= 0.0:
            raise ValueError("Waveform window must be positive.")
        if self.ANIMATION_FRAME_COUNT < 3:
            raise ValueError("Animation frame count must be at least 3.")
        if self.ANIMATION_FPS <= 0:
            raise ValueError("Animation FPS must be positive.")
        if self.ANIMATION_DPI <= 0:
            raise ValueError("Animation DPI must be positive.")
        if self.ANIMATION_WAVEFORM_WINDOW_S <= 0.0:
            raise ValueError("Animation waveform window must be positive.")
        if self.ROTOR_ANIMATION_FRAME_COUNT < 3:
            raise ValueError("Rotor animation frame count must be at least 3.")
        if self.ROTOR_ANIMATION_FPS <= 0:
            raise ValueError("Rotor animation FPS must be positive.")
        if self.ROTOR_DISPLAY_FREQUENCY_HZ <= 0.0:
            raise ValueError("Rotor display frequency must be positive.")
        if self.ROTOR_ANIMATION_PRE_STEP_TIME_S <= 0.0:
            raise ValueError("Rotor animation pre-step time must be positive.")
        if self.ROTOR_ANIMATION_POST_STEP_TIME_S <= 0.0:
            raise ValueError("Rotor animation post-step time must be positive.")
        if self.SLOW_MOTION_REFERENCE_FREQUENCY_HZ <= 0.0:
            raise ValueError("Slow-motion reference frequency must be positive.")
        if self.SLIP_ANIMATION_PRE_STEP_TIME_S <= 0.0:
            raise ValueError("Slip animation pre-step time must be positive.")
        if self.SLIP_ANIMATION_DURATION_S <= 0.0:
            raise ValueError("Slip animation duration must be positive.")
        if self.SLIP_ANIMATION_FRAME_COUNT < 3:
            raise ValueError("Slip animation frame count must be at least 3.")
        if self.SLIP_ANIMATION_FPS <= 0:
            raise ValueError("Slip animation FPS must be positive.")

    @property
    def omega_nominal_rad_per_s(self) -> float:
        """Return the nominal electrical angular frequency in rad/s."""
        return 2.0 * math.pi * self.F_NOM_HZ

    @property
    def phase_voltage_rms(self) -> float:
        """Return the nominal phase-to-neutral RMS voltage."""
        return self.V_LL_RMS / math.sqrt(3.0)

    @property
    def impedance_base_ohm(self) -> float:
        """Return the three-phase impedance base in ohms."""
        return self.V_LL_RMS**2 / self.S_BASE_VA

    @property
    def stator_resistance_ohm(self) -> float:
        """Return the simplified stator resistance in ohms."""
        return self.STATOR_RESISTANCE_PU * self.impedance_base_ohm

    @property
    def synchronous_reactance_ohm(self) -> float:
        """Return the simplified synchronous reactance in ohms."""
        return self.SYNCHRONOUS_REACTANCE_PU * self.impedance_base_ohm

    @property
    def initial_active_power_pu(self) -> float:
        """Return active power pu consumed by the initial impedance at nominal voltage."""
        return self.nominal_voltage_active_power_pu(self.INITIAL_LOAD_PU, self.INITIAL_LOAD_ANGLE_DEG)

    @property
    def final_active_power_pu(self) -> float:
        """Return active power pu consumed by the final impedance at nominal voltage."""
        return self.nominal_voltage_active_power_pu(self.final_load_pu, self.final_load_angle_deg)

    @property
    def initial_power_w(self) -> float:
        """Return the initial three-phase active power in watts."""
        return self.initial_active_power_pu * self.S_BASE_VA

    @property
    def final_power_w(self) -> float:
        """Return the final three-phase active power in watts."""
        return self.final_active_power_pu * self.S_BASE_VA

    @property
    def initial_impedance_ohm(self) -> complex:
        """Return the initial phase load impedance in ohms."""
        return self.impedance_for_load_pu(self.INITIAL_LOAD_PU, self.INITIAL_LOAD_ANGLE_DEG)

    @property
    def first_step_impedance_ohm(self) -> complex:
        """Return the phase load impedance after the first load step."""
        return self.impedance_for_load_pu(self.FINAL_LOAD_PU, self.FINAL_LOAD_ANGLE_DEG)

    @property
    def second_step_impedance_ohm(self) -> complex:
        """Return the phase load impedance after the second load step."""
        if self.SECOND_STEP_LOAD_PU is None or self.SECOND_STEP_LOAD_ANGLE_DEG is None:
            return self.first_step_impedance_ohm
        return self.impedance_for_load_pu(self.SECOND_STEP_LOAD_PU, self.SECOND_STEP_LOAD_ANGLE_DEG)

    @property
    def final_impedance_ohm(self) -> complex:
        """Return the final phase load impedance in ohms."""
        return self.impedance_for_load_pu(self.final_load_pu, self.final_load_angle_deg)

    @property
    def initial_resistance_ohm(self) -> float:
        """Return the real part of the initial phase load impedance."""
        return self.initial_impedance_ohm.real

    @property
    def first_step_resistance_ohm(self) -> float:
        """Return the real part of the first-step phase load impedance."""
        return self.first_step_impedance_ohm.real

    @property
    def final_resistance_ohm(self) -> float:
        """Return the real part of the final phase load impedance."""
        return self.final_impedance_ohm.real

    @property
    def additional_load_steps(self) -> tuple[tuple[float, float, float], ...]:
        """Return active load steps after the first disturbance."""
        if self.ADDITIONAL_LOAD_STEPS is not None:
            return self.ADDITIONAL_LOAD_STEPS
        active_steps: list[tuple[float, float, float]] = []
        if (
            self.SECOND_LOAD_STEP_TIME_S is not None
            and self.SECOND_STEP_LOAD_PU is not None
            and self.SECOND_STEP_LOAD_ANGLE_DEG is not None
        ):
            active_steps.append(
                (self.SECOND_LOAD_STEP_TIME_S, self.SECOND_STEP_LOAD_PU, self.SECOND_STEP_LOAD_ANGLE_DEG)
            )
        if (
            self.THIRD_LOAD_STEP_TIME_S is not None
            and self.THIRD_STEP_LOAD_PU is not None
            and self.THIRD_STEP_LOAD_ANGLE_DEG is not None
        ):
            active_steps.append(
                (self.THIRD_LOAD_STEP_TIME_S, self.THIRD_STEP_LOAD_PU, self.THIRD_STEP_LOAD_ANGLE_DEG)
            )
        return tuple(active_steps)

    @property
    def load_schedule(self) -> tuple[tuple[float, float, float], ...]:
        """Return the full load schedule as (time_s, impedance_magnitude_pu, angle_deg)."""
        return (
            (0.0, self.INITIAL_LOAD_PU, self.INITIAL_LOAD_ANGLE_DEG),
            (self.LOAD_STEP_TIME_S, self.FINAL_LOAD_PU, self.FINAL_LOAD_ANGLE_DEG),
            *self.additional_load_steps,
        )

    @property
    def load_step_times_s(self) -> tuple[float, ...]:
        """Return all non-initial load-step times."""
        return tuple(step_time_s for step_time_s, _, _ in self.load_schedule[1:])

    @property
    def final_load_pu(self) -> float:
        """Return the load impedance magnitude in the final schedule segment."""
        return self.load_schedule[-1][1]

    @property
    def final_load_angle_deg(self) -> float:
        """Return the load impedance angle in the final schedule segment."""
        return self.load_schedule[-1][2]

    @property
    def final_load_step_time_s(self) -> float:
        """Return the time of the last load step."""
        return self.load_step_times_s[-1]

    def impedance_for_load_pu(self, load_impedance_pu: float, load_angle_deg: float) -> complex:
        """Return phase impedance in ohms from per-unit magnitude and angle."""
        angle_rad = math.radians(load_angle_deg)
        magnitude_ohm = load_impedance_pu * self.impedance_base_ohm
        return magnitude_ohm * complex(math.cos(angle_rad), math.sin(angle_rad))

    def nominal_voltage_active_power_pu(self, load_impedance_pu: float, load_angle_deg: float) -> float:
        """Return active power pu consumed by the impedance at nominal terminal voltage."""
        return math.cos(math.radians(load_angle_deg)) / load_impedance_pu

    def nominal_voltage_reactive_power_pu(self, load_impedance_pu: float, load_angle_deg: float) -> float:
        """Return reactive power pu consumed by the impedance at nominal terminal voltage."""
        return math.sin(math.radians(load_angle_deg)) / load_impedance_pu
