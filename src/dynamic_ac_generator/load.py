"""Balanced three-phase impedance load model."""

from __future__ import annotations

import numpy as np

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.model_types import ComplexArray, FloatArray


class ImpedanceLoad:
    """Balanced star-connected three-phase load represented by complex impedance."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config

    def impedance_pu(
        self,
        magnitude_pu: float | FloatArray,
        angle_deg: float | FloatArray,
    ) -> complex | ComplexArray:
        """Return complex per-unit impedance from magnitude and angle."""
        magnitude_array = np.asarray(magnitude_pu, dtype=float)
        angle_array_rad = np.deg2rad(np.asarray(angle_deg, dtype=float))
        impedance = magnitude_array * (np.cos(angle_array_rad) + 1j * np.sin(angle_array_rad))
        if np.isscalar(magnitude_pu) and np.isscalar(angle_deg):
            return complex(impedance)
        return impedance.astype(complex)

    def impedance_ohm(
        self,
        magnitude_pu: float | FloatArray,
        angle_deg: float | FloatArray,
    ) -> complex | ComplexArray:
        """Return phase impedance in ohms from per-unit magnitude and angle."""
        return self.impedance_pu(magnitude_pu, angle_deg) * self.config.impedance_base_ohm

    def impedance_magnitude_pu_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return load impedance magnitude in per unit at a time or array of times."""
        time_array = np.asarray(time_s, dtype=float)
        magnitude_values = np.full_like(time_array, self.config.INITIAL_LOAD_PU, dtype=float)
        for step_time_s, load_impedance_pu, _ in self.config.load_schedule[1:]:
            magnitude_values = np.where(time_array < step_time_s, magnitude_values, load_impedance_pu)
        if np.isscalar(time_s):
            return float(magnitude_values)
        return magnitude_values.astype(float)

    def impedance_angle_deg_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return load impedance angle in degrees at a time or array of times."""
        time_array = np.asarray(time_s, dtype=float)
        angle_values = np.full_like(time_array, self.config.INITIAL_LOAD_ANGLE_DEG, dtype=float)
        for step_time_s, _, load_angle_deg in self.config.load_schedule[1:]:
            angle_values = np.where(time_array < step_time_s, angle_values, load_angle_deg)
        if np.isscalar(time_s):
            return float(angle_values)
        return angle_values.astype(float)

    def impedance_pu_at(self, time_s: float | FloatArray) -> complex | ComplexArray:
        """Return complex load impedance in per unit at a time or array of times."""
        return self.impedance_pu(
            self.impedance_magnitude_pu_at(time_s),
            self.impedance_angle_deg_at(time_s),
        )

    def impedance_at(self, time_s: float | FloatArray) -> complex | ComplexArray:
        """Return complex phase impedance in ohms at a time or array of times."""
        return self.impedance_pu_at(time_s) * self.config.impedance_base_ohm

    def impedance_magnitude_ohm_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return load impedance magnitude in ohms at a time or array of times."""
        magnitude = self.impedance_magnitude_pu_at(time_s)
        return magnitude * self.config.impedance_base_ohm

    def nominal_voltage_active_power_pu_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return active power pu consumed by the load at nominal terminal voltage."""
        magnitude = np.asarray(self.impedance_magnitude_pu_at(time_s), dtype=float)
        angle_rad = np.deg2rad(np.asarray(self.impedance_angle_deg_at(time_s), dtype=float))
        active_power = np.cos(angle_rad) / magnitude
        if np.isscalar(time_s):
            return float(active_power)
        return active_power.astype(float)

    def nominal_voltage_reactive_power_pu_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return reactive power pu consumed by the load at nominal terminal voltage."""
        magnitude = np.asarray(self.impedance_magnitude_pu_at(time_s), dtype=float)
        angle_rad = np.deg2rad(np.asarray(self.impedance_angle_deg_at(time_s), dtype=float))
        reactive_power = np.sin(angle_rad) / magnitude
        if np.isscalar(time_s):
            return float(reactive_power)
        return reactive_power.astype(float)

    def resistance_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return the real part of the phase impedance for backward-compatible callers."""
        impedance = self.impedance_at(time_s)
        return np.real(impedance)

    def electrical_power_pu_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return nominal-voltage active power in per unit for backward-compatible callers."""
        return self.nominal_voltage_active_power_pu_at(time_s)


ResistiveLoad = ImpedanceLoad
