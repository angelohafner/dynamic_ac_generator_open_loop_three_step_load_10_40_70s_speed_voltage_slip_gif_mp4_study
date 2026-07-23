"""Simplified AC generator equations and waveform calculations."""

from __future__ import annotations

import math

import numpy as np

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.electrical import TerminalElectricalModel
from dynamic_ac_generator.excitation import OpenLoopExcitationModel
from dynamic_ac_generator.governor import IsochronousGovernor
from dynamic_ac_generator.load import ResistiveLoad
from dynamic_ac_generator.model_types import FloatArray


class GeneratorModel:
    """Simplified synchronous generator model for active-power balance studies."""

    def __init__(
        self,
        config: SimulationConfig,
        load: ResistiveLoad,
        governor: IsochronousGovernor | None,
        electrical_model: TerminalElectricalModel | None = None,
    ) -> None:
        self.config = config
        self.load = load
        self.governor = governor
        self.electrical_model = electrical_model or TerminalElectricalModel(
            config,
            OpenLoopExcitationModel(config),
        )

    def state_derivatives(self, time_s: float, state: FloatArray) -> list[float]:
        """Return the derivatives of the dynamic state vector."""
        omega_pu = float(state[0])
        integral_state = float(state[1])
        mechanical_power_pu = float(state[2])
        field_current_pu = float(state[4])

        load_impedance_ohm = complex(self.load.impedance_at(time_s))
        terminal_quantities = self.electrical_model.solve_terminal_quantities(
            load_impedance_ohm,
            field_current_pu,
            omega_pu,
        )
        electrical_power_pu = terminal_quantities.electrical_power_pu
        if self.governor is None:
            reference_power_pu = mechanical_power_pu
            integral_derivative_pu = 0.0
            mechanical_power_derivative_pu_per_s = 0.0
        else:
            reference_power_pu = float(self.governor.limited_reference_power_pu(omega_pu, integral_state))
            integral_derivative_pu = self.governor.integral_derivative_pu(omega_pu, integral_state)
            mechanical_power_derivative_pu_per_s = (
                reference_power_pu - mechanical_power_pu
            ) / self.config.T_M

        speed_derivative_pu_per_s = (
            mechanical_power_pu
            - electrical_power_pu
            - self.config.D * (omega_pu - 1.0)
        ) / (2.0 * self.config.H)
        angle_derivative_rad_per_s = self.config.omega_nominal_rad_per_s * omega_pu
        field_current_derivative_pu_per_s = 0.0

        return [
            speed_derivative_pu_per_s,
            integral_derivative_pu,
            mechanical_power_derivative_pu_per_s,
            angle_derivative_rad_per_s,
            field_current_derivative_pu_per_s,
        ]

    def three_phase_voltages(
        self,
        theta_rad: FloatArray,
        phase_voltage_rms: FloatArray | None = None,
        phase_angle_rad: FloatArray | None = None,
    ) -> tuple[FloatArray, FloatArray, FloatArray]:
        """Generate balanced phase-to-neutral voltages from rotor angle."""
        theta_wrapped_rad = np.mod(theta_rad + math.pi, 2.0 * math.pi) - math.pi
        active_phase_voltage_rms = (
            self.config.phase_voltage_rms
            if phase_voltage_rms is None
            else np.asarray(phase_voltage_rms, dtype=float)
        )
        active_phase_angle_rad = (
            0.0
            if phase_angle_rad is None
            else np.asarray(phase_angle_rad, dtype=float)
        )
        voltage_peak = math.sqrt(2.0) * active_phase_voltage_rms
        terminal_angle_rad = theta_wrapped_rad + active_phase_angle_rad
        voltage_a_v = voltage_peak * np.sin(terminal_angle_rad)
        voltage_b_v = voltage_peak * np.sin(terminal_angle_rad - 2.0 * math.pi / 3.0)
        voltage_c_v = voltage_peak * np.sin(terminal_angle_rad + 2.0 * math.pi / 3.0)
        return voltage_a_v, voltage_b_v, voltage_c_v

    def phase_currents(
        self,
        voltage_a_v: FloatArray,
        voltage_b_v: FloatArray,
        voltage_c_v: FloatArray,
        resistance_ohm: FloatArray,
    ) -> tuple[FloatArray, FloatArray, FloatArray]:
        """Calculate in-phase currents for backward-compatible resistive-only callers."""
        current_a_a = voltage_a_v / resistance_ohm
        current_b_a = voltage_b_v / resistance_ohm
        current_c_a = voltage_c_v / resistance_ohm
        return current_a_a, current_b_a, current_c_a

    def three_phase_currents(
        self,
        theta_rad: FloatArray,
        current_phase_rms: FloatArray,
        current_angle_rad: FloatArray,
    ) -> tuple[FloatArray, FloatArray, FloatArray]:
        """Generate balanced phase currents from the current phasor angle."""
        theta_wrapped_rad = np.mod(theta_rad + math.pi, 2.0 * math.pi) - math.pi
        current_peak = math.sqrt(2.0) * np.asarray(current_phase_rms, dtype=float)
        active_current_angle_rad = np.asarray(current_angle_rad, dtype=float)
        current_a_a = current_peak * np.sin(theta_wrapped_rad + active_current_angle_rad)
        current_b_a = current_peak * np.sin(theta_wrapped_rad + active_current_angle_rad - 2.0 * math.pi / 3.0)
        current_c_a = current_peak * np.sin(theta_wrapped_rad + active_current_angle_rad + 2.0 * math.pi / 3.0)
        return current_a_a, current_b_a, current_c_a
