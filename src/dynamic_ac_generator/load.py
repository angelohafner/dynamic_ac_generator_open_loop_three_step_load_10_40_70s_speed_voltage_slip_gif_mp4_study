"""Balanced three-phase load models."""

from __future__ import annotations

import numpy as np

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.model_types import ComplexArray, FloatArray


class ImpedanceLoad:
    """Balanced star-connected three-phase load with configurable load semantics."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config

    def impedance_pu(
        self,
        load_value_pu: float | FloatArray,
        angle_deg: float | FloatArray,
    ) -> complex | ComplexArray:
        """Return complex per-unit impedance from the configured load semantics."""
        if self.config.LOAD_MODEL == "parallel_admittance":
            admittance = self.admittance_pu(load_value_pu, angle_deg)
            return 1.0 / admittance
        magnitude_array = np.asarray(load_value_pu, dtype=float)
        angle_array_rad = np.deg2rad(np.asarray(angle_deg, dtype=float))
        impedance = magnitude_array * (np.cos(angle_array_rad) + 1j * np.sin(angle_array_rad))
        if np.isscalar(load_value_pu) and np.isscalar(angle_deg):
            return complex(impedance)
        return impedance.astype(complex)

    def impedance_ohm(
        self,
        load_value_pu: float | FloatArray,
        angle_deg: float | FloatArray,
    ) -> complex | ComplexArray:
        """Return phase impedance in ohms from the configured load semantics."""
        return self.impedance_pu(load_value_pu, angle_deg) * self.config.impedance_base_ohm

    def load_value_pu_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return the configured load value at a time or array of times."""
        time_array = np.asarray(time_s, dtype=float)
        load_values = np.full_like(time_array, self.config.INITIAL_LOAD_PU, dtype=float)
        for step_time_s, load_value_pu, _ in self.config.load_schedule[1:]:
            load_values = np.where(time_array < step_time_s, load_values, load_value_pu)
        if np.isscalar(time_s):
            return float(load_values)
        return load_values.astype(float)

    def load_angle_deg_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return the configured load angle in degrees at a time or array of times."""
        time_array = np.asarray(time_s, dtype=float)
        angle_values = np.full_like(time_array, self.config.INITIAL_LOAD_ANGLE_DEG, dtype=float)
        for step_time_s, _, load_angle_deg in self.config.load_schedule[1:]:
            angle_values = np.where(time_array < step_time_s, angle_values, load_angle_deg)
        if np.isscalar(time_s):
            return float(angle_values)
        return angle_values.astype(float)

    def admittance_pu(
        self,
        load_value_pu: float | FloatArray,
        angle_deg: float | FloatArray,
    ) -> complex | ComplexArray:
        """Return complex per-unit load admittance from the configured semantics."""
        value_array = np.asarray(load_value_pu, dtype=float)
        angle_array_rad = np.deg2rad(np.asarray(angle_deg, dtype=float))
        if self.config.LOAD_MODEL == "series_impedance":
            impedance = value_array * (np.cos(angle_array_rad) + 1j * np.sin(angle_array_rad))
            admittance = 1.0 / impedance
        else:
            reactive_power = value_array * np.tan(angle_array_rad)
            admittance = value_array - 1j * reactive_power
        if np.isscalar(load_value_pu) and np.isscalar(angle_deg):
            return complex(admittance)
        return admittance.astype(complex)

    def admittance_pu_at(self, time_s: float | FloatArray) -> complex | ComplexArray:
        """Return complex load admittance in per unit at a time or array of times."""
        return self.admittance_pu(
            self.load_value_pu_at(time_s),
            self.load_angle_deg_at(time_s),
        )

    def admittance_magnitude_pu_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return load admittance magnitude in per unit at a time or array of times."""
        admittance = self.admittance_pu_at(time_s)
        magnitude = np.abs(admittance)
        if np.isscalar(time_s):
            return float(magnitude)
        return magnitude.astype(float)

    def admittance_angle_deg_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return load admittance angle in degrees at a time or array of times."""
        admittance = self.admittance_pu_at(time_s)
        angle_deg = np.rad2deg(np.angle(admittance))
        if np.isscalar(time_s):
            return float(angle_deg)
        return angle_deg.astype(float)

    def conductance_pu_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return load conductance in per unit at a time or array of times."""
        conductance = np.real(self.admittance_pu_at(time_s))
        if np.isscalar(time_s):
            return float(conductance)
        return conductance.astype(float)

    def susceptance_pu_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return load susceptance in per unit at a time or array of times."""
        susceptance = np.imag(self.admittance_pu_at(time_s))
        if np.isscalar(time_s):
            return float(susceptance)
        return susceptance.astype(float)

    def impedance_magnitude_pu_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return equivalent load impedance magnitude in per unit at a time or array of times."""
        impedance = self.impedance_pu_at(time_s)
        magnitude = np.abs(impedance)
        if np.isscalar(time_s):
            return float(magnitude)
        return magnitude.astype(float)

    def impedance_angle_deg_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return equivalent load impedance angle in degrees at a time or array of times."""
        impedance = self.impedance_pu_at(time_s)
        angle_deg = np.rad2deg(np.angle(impedance))
        if np.isscalar(time_s):
            return float(angle_deg)
        return angle_deg.astype(float)

    def impedance_pu_at(self, time_s: float | FloatArray) -> complex | ComplexArray:
        """Return complex equivalent load impedance in per unit at a time or array of times."""
        return self.impedance_pu(
            self.load_value_pu_at(time_s),
            self.load_angle_deg_at(time_s),
        )

    def impedance_at(self, time_s: float | FloatArray) -> complex | ComplexArray:
        """Return complex equivalent phase impedance in ohms at a time or array of times."""
        return self.impedance_pu_at(time_s) * self.config.impedance_base_ohm

    def impedance_magnitude_ohm_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return equivalent load impedance magnitude in ohms at a time or array of times."""
        magnitude = self.impedance_magnitude_pu_at(time_s)
        return magnitude * self.config.impedance_base_ohm

    def nominal_voltage_active_power_pu_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return active power pu consumed by the load at nominal terminal voltage."""
        load_value = np.asarray(self.load_value_pu_at(time_s), dtype=float)
        angle_rad = np.deg2rad(np.asarray(self.load_angle_deg_at(time_s), dtype=float))
        if self.config.LOAD_MODEL == "series_impedance":
            active_power = np.cos(angle_rad) / load_value
        else:
            active_power = load_value
        if np.isscalar(time_s):
            return float(active_power)
        return active_power.astype(float)

    def nominal_voltage_reactive_power_pu_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return reactive power pu consumed by the load at nominal terminal voltage."""
        load_value = np.asarray(self.load_value_pu_at(time_s), dtype=float)
        angle_rad = np.deg2rad(np.asarray(self.load_angle_deg_at(time_s), dtype=float))
        if self.config.LOAD_MODEL == "series_impedance":
            reactive_power = np.sin(angle_rad) / load_value
        else:
            reactive_power = load_value * np.tan(angle_rad)
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
