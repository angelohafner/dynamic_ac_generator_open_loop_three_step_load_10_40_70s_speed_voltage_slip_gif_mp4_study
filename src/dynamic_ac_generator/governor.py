"""Isochronous PI governor model."""

from __future__ import annotations

import numpy as np

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.model_types import FloatArray


class IsochronousGovernor:
    """PI speed governor with mechanical power limits and anti-windup."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config

    def speed_error_pu(self, omega_pu: float | FloatArray) -> float | FloatArray:
        """Calculate the governor speed error."""
        return 1.0 - omega_pu

    def raw_reference_power_pu(
        self,
        omega_pu: float | FloatArray,
        integral_state: float | FloatArray,
    ) -> float | FloatArray:
        """Calculate the unlimited mechanical power reference in per unit."""
        error_pu = self.speed_error_pu(omega_pu)
        return self.config.initial_active_power_pu + self.config.KP * error_pu + self.config.KI * integral_state

    def limited_reference_power_pu(
        self,
        omega_pu: float | FloatArray,
        integral_state: float | FloatArray,
    ) -> float | FloatArray:
        """Apply mechanical power limits to the reference power."""
        raw_reference = self.raw_reference_power_pu(omega_pu, integral_state)
        limited_reference = np.clip(raw_reference, self.config.P_M_MIN_PU, self.config.P_M_MAX_PU)
        if np.isscalar(raw_reference):
            return float(limited_reference)
        return limited_reference.astype(float)

    def integral_derivative_pu(self, omega_pu: float, integral_state: float) -> float:
        """Calculate the anti-windup integral derivative."""
        error_pu = float(self.speed_error_pu(omega_pu))
        raw_reference = float(self.raw_reference_power_pu(omega_pu, integral_state))
        saturated_high = raw_reference >= self.config.P_M_MAX_PU and error_pu > 0.0
        saturated_low = raw_reference <= self.config.P_M_MIN_PU and error_pu < 0.0
        if saturated_high or saturated_low:
            return 0.0
        return error_pu
