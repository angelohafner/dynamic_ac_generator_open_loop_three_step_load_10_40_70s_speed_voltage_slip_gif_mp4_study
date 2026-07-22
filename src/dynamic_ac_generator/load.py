"""Balanced three-phase resistive load model."""

from __future__ import annotations

import numpy as np

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.model_types import FloatArray


class ResistiveLoad:
    """Balanced star-connected three-phase resistive load."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config

    def active_power_w(self, load_power_pu: float | FloatArray) -> float | FloatArray:
        """Convert load active power from per unit to watts."""
        return load_power_pu * self.config.S_BASE_VA

    def phase_resistance_ohm(self, load_power_pu: float | FloatArray) -> float | FloatArray:
        """Calculate phase resistance for the requested per-unit active power."""
        active_power_w = self.active_power_w(load_power_pu)
        return 3.0 * self.config.phase_voltage_rms**2 / active_power_w

    def load_power_pu_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return the load active power in per unit at a time or array of times."""
        time_array = np.asarray(time_s, dtype=float)
        load_values = np.full_like(time_array, self.config.INITIAL_LOAD_PU, dtype=float)
        for step_time_s, load_power_pu in self.config.load_schedule[1:]:
            load_values = np.where(time_array < step_time_s, load_values, load_power_pu)
        if np.isscalar(time_s):
            return float(load_values)
        return load_values.astype(float)

    def resistance_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return the phase resistance in ohms at a time or array of times."""
        return self.phase_resistance_ohm(self.load_power_pu_at(time_s))

    def electrical_power_pu_at(self, time_s: float | FloatArray) -> float | FloatArray:
        """Return the three-phase electrical power in per unit."""
        resistance_ohm = self.resistance_at(time_s)
        active_power_w = 3.0 * self.config.phase_voltage_rms**2 / resistance_ohm
        return active_power_w / self.config.S_BASE_VA
