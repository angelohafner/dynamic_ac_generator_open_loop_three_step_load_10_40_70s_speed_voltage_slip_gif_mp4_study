"""Terminal electrical model for the simplified open-loop generator."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.excitation import OpenLoopExcitationModel
from dynamic_ac_generator.model_types import FloatArray


@dataclass(frozen=True)
class TerminalQuantities:
    """Balanced steady-state terminal quantities for one load point."""

    field_current_pu: float
    omega_pu: float
    internal_voltage_phase_rms: float
    internal_voltage_ll_rms: float
    terminal_voltage_phase_rms: float
    terminal_voltage_ll_rms: float
    terminal_voltage_angle_rad: float
    load_current_phase_rms: float
    electrical_power_pu: float


class TerminalElectricalModel:
    """Solve terminal voltage behind a fixed internal impedance."""

    def __init__(
        self,
        config: SimulationConfig,
        excitation: OpenLoopExcitationModel,
    ) -> None:
        self.config = config
        self.excitation = excitation

    @property
    def series_impedance_ohm(self) -> complex:
        """Return the simplified per-phase internal impedance."""
        return complex(
            self.config.stator_resistance_ohm,
            self.config.synchronous_reactance_ohm,
        )

    def solve_terminal_quantities(
        self,
        load_resistance_ohm: float,
        field_current_pu: float,
        omega_pu: float = 1.0,
    ) -> TerminalQuantities:
        """Solve phase RMS terminal voltage, current, and active power."""
        internal_voltage_phase_rms = self.excitation.internal_voltage_phase_rms(
            field_current_pu,
            omega_pu,
        )
        internal_voltage = complex(internal_voltage_phase_rms, 0.0)
        current = internal_voltage / (complex(load_resistance_ohm, 0.0) + self.series_impedance_ohm)
        terminal_voltage = current * load_resistance_ohm
        terminal_voltage_phase_rms = abs(terminal_voltage)
        load_current_phase_rms = abs(current)
        electrical_power_w = 3.0 * terminal_voltage_phase_rms**2 / load_resistance_ohm
        return TerminalQuantities(
            field_current_pu=field_current_pu,
            omega_pu=omega_pu,
            internal_voltage_phase_rms=internal_voltage_phase_rms,
            internal_voltage_ll_rms=math.sqrt(3.0) * internal_voltage_phase_rms,
            terminal_voltage_phase_rms=terminal_voltage_phase_rms,
            terminal_voltage_ll_rms=math.sqrt(3.0) * terminal_voltage_phase_rms,
            terminal_voltage_angle_rad=math.atan2(terminal_voltage.imag, terminal_voltage.real),
            load_current_phase_rms=load_current_phase_rms,
            electrical_power_pu=electrical_power_w / self.config.S_BASE_VA,
        )

    def terminal_quantities_at(
        self,
        load_resistance_ohm: FloatArray,
        field_current_pu: FloatArray,
        omega_pu: FloatArray,
    ) -> dict[str, FloatArray]:
        """Return vectorized terminal quantities for arrays of load and field current."""
        load_array = np.asarray(load_resistance_ohm, dtype=float)
        field_array = np.asarray(field_current_pu, dtype=float)
        omega_array = np.asarray(omega_pu, dtype=float)
        internal_phase_rms = self.excitation.excitation_gain_phase_rms * field_array * omega_array
        internal_voltage = internal_phase_rms.astype(complex)
        current = internal_voltage / (load_array.astype(complex) + self.series_impedance_ohm)
        terminal_voltage = current * load_array
        terminal_phase_rms = np.abs(terminal_voltage)
        current_phase_rms = np.abs(current)
        electrical_power_pu = 3.0 * terminal_phase_rms**2 / load_array / self.config.S_BASE_VA
        return {
            "internal_voltage_phase_rms": internal_phase_rms.astype(float),
            "internal_voltage_ll_rms": (math.sqrt(3.0) * internal_phase_rms).astype(float),
            "terminal_voltage_phase_rms": terminal_phase_rms.astype(float),
            "terminal_voltage_ll_rms": (math.sqrt(3.0) * terminal_phase_rms).astype(float),
            "terminal_voltage_angle_rad": np.angle(terminal_voltage).astype(float),
            "load_current_phase_rms": current_phase_rms.astype(float),
            "electrical_power_pu": electrical_power_pu.astype(float),
        }
