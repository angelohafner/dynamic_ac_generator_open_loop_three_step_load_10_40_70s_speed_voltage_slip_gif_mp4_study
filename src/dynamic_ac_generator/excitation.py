"""Open-loop excitation model for the simplified generator."""

from __future__ import annotations

import math

from dynamic_ac_generator.config import SimulationConfig


class OpenLoopExcitationModel:
    """Represent E = K_e * I_f * omega with no automatic voltage regulator."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config

    @property
    def excitation_gain_phase_rms(self) -> float:
        """Return K_e in phase RMS volts per field-current pu and speed pu."""
        initial_impedance_ohm = self.config.initial_impedance_ohm
        series_impedance = complex(
            self.config.stator_resistance_ohm,
            self.config.synchronous_reactance_ohm,
        )
        voltage_ratio = initial_impedance_ohm / (initial_impedance_ohm + series_impedance)
        required_internal_phase_voltage = self.config.phase_voltage_rms / abs(voltage_ratio)
        return required_internal_phase_voltage / self.config.FIELD_CURRENT_INITIAL_PU

    def internal_voltage_phase_rms(
        self,
        field_current_pu: float,
        omega_pu: float = 1.0,
    ) -> float:
        """Return internal generated phase RMS voltage."""
        return self.excitation_gain_phase_rms * field_current_pu * omega_pu

    def internal_voltage_ll_rms(
        self,
        field_current_pu: float,
        omega_pu: float = 1.0,
    ) -> float:
        """Return internal generated line-to-line RMS voltage."""
        return math.sqrt(3.0) * self.internal_voltage_phase_rms(field_current_pu, omega_pu)
