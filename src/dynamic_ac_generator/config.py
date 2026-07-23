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
    P_M_MAX_PU: float = 1.2

    INITIAL_LOAD_PU: float = 0.50
    FINAL_LOAD_PU: float = 0.80
    SECOND_LOAD_STEP_TIME_S: float | None = 40.0
    SECOND_STEP_LOAD_PU: float | None = 0.20
    THIRD_LOAD_STEP_TIME_S: float | None = 70.0
    THIRD_STEP_LOAD_PU: float | None = 0.50
    ADDITIONAL_LOAD_STEPS: tuple[tuple[float, float], ...] | None = None

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
        if self.DAMPED_COMPARISON_D <= self.FINAL_LOAD_PU - self.INITIAL_LOAD_PU:
            raise ValueError("Damped comparison coefficient must produce a positive final frequency.")
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
            raise ValueError("Initial load power must be positive.")
        if self.FINAL_LOAD_PU <= 0.0:
            raise ValueError("Final load power must be positive.")
        if self.SECOND_LOAD_STEP_TIME_S is None and self.SECOND_STEP_LOAD_PU is not None:
            raise ValueError("Second load power requires a second load-step time.")
        if self.SECOND_LOAD_STEP_TIME_S is not None and self.SECOND_STEP_LOAD_PU is None:
            raise ValueError("Second load-step time requires a second load power.")
        if self.SECOND_STEP_LOAD_PU is not None and self.SECOND_STEP_LOAD_PU <= 0.0:
            raise ValueError("Second load power must be positive.")
        if self.THIRD_LOAD_STEP_TIME_S is None and self.THIRD_STEP_LOAD_PU is not None:
            raise ValueError("Third load power requires a third load-step time.")
        if self.THIRD_LOAD_STEP_TIME_S is not None and self.THIRD_STEP_LOAD_PU is None:
            raise ValueError("Third load-step time requires a third load power.")
        if self.THIRD_STEP_LOAD_PU is not None and self.THIRD_STEP_LOAD_PU <= 0.0:
            raise ValueError("Third load power must be positive.")
        if not (self.P_M_MIN_PU <= self.INITIAL_LOAD_PU <= self.P_M_MAX_PU):
            raise ValueError("Initial load must be inside the mechanical power limits.")
        if self.FINAL_LOAD_PU > self.P_M_MAX_PU:
            raise ValueError("Final load must not exceed the maximum mechanical power for this recovery case.")
        if not (0.0 < self.LOAD_STEP_TIME_S < self.SIMULATION_TIME_S):
            raise ValueError("Load step time must be greater than zero and lower than the simulation time.")
        previous_step_time_s = self.LOAD_STEP_TIME_S
        for step_time_s, load_power_pu in self.additional_load_steps:
            if load_power_pu <= 0.0:
                raise ValueError("Additional load powers must be positive.")
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
    def initial_power_w(self) -> float:
        """Return the initial three-phase active power in watts."""
        return self.INITIAL_LOAD_PU * self.S_BASE_VA

    @property
    def final_power_w(self) -> float:
        """Return the final three-phase active power in watts."""
        return self.final_load_pu * self.S_BASE_VA

    @property
    def initial_resistance_ohm(self) -> float:
        """Return the initial phase resistance in ohms."""
        return self.resistance_for_load_power_pu(self.INITIAL_LOAD_PU)

    @property
    def first_step_resistance_ohm(self) -> float:
        """Return the phase resistance after the first load step."""
        return self.resistance_for_load_power_pu(self.FINAL_LOAD_PU)

    @property
    def final_resistance_ohm(self) -> float:
        """Return the final phase resistance in ohms."""
        return self.resistance_for_load_power_pu(self.final_load_pu)

    @property
    def additional_load_steps(self) -> tuple[tuple[float, float], ...]:
        """Return active load steps after the first disturbance."""
        if self.ADDITIONAL_LOAD_STEPS is not None:
            return self.ADDITIONAL_LOAD_STEPS
        active_steps: list[tuple[float, float]] = []
        if self.SECOND_LOAD_STEP_TIME_S is not None and self.SECOND_STEP_LOAD_PU is not None:
            active_steps.append((self.SECOND_LOAD_STEP_TIME_S, self.SECOND_STEP_LOAD_PU))
        if self.THIRD_LOAD_STEP_TIME_S is not None and self.THIRD_STEP_LOAD_PU is not None:
            active_steps.append((self.THIRD_LOAD_STEP_TIME_S, self.THIRD_STEP_LOAD_PU))
        return tuple(active_steps)

    @property
    def load_schedule(self) -> tuple[tuple[float, float], ...]:
        """Return the full load schedule as (time_s, load_power_pu) pairs."""
        return (
            (0.0, self.INITIAL_LOAD_PU),
            (self.LOAD_STEP_TIME_S, self.FINAL_LOAD_PU),
            *self.additional_load_steps,
        )

    @property
    def load_step_times_s(self) -> tuple[float, ...]:
        """Return all non-initial load-step times."""
        return tuple(step_time_s for step_time_s, _ in self.load_schedule[1:])

    @property
    def final_load_pu(self) -> float:
        """Return the active load power in the final schedule segment."""
        return self.load_schedule[-1][1]

    @property
    def final_load_step_time_s(self) -> float:
        """Return the time of the last load step."""
        return self.load_step_times_s[-1]

    def resistance_for_load_power_pu(self, load_power_pu: float) -> float:
        """Return phase resistance for a nominal-voltage load power."""
        return 3.0 * self.phase_voltage_rms**2 / (load_power_pu * self.S_BASE_VA)
