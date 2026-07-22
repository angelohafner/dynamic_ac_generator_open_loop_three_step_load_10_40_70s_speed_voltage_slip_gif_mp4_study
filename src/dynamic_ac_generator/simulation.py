"""Numerical integration and waveform reconstruction."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.electrical import TerminalElectricalModel
from dynamic_ac_generator.excitation import OpenLoopExcitationModel
from dynamic_ac_generator.generator import GeneratorModel
from dynamic_ac_generator.governor import IsochronousGovernor
from dynamic_ac_generator.load import ResistiveLoad
from dynamic_ac_generator.model_types import FloatArray
from dynamic_ac_generator.results import SimulationResults


class DynamicSimulation:
    """Solve the generator dynamics and reconstruct electrical waveforms."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.load = ResistiveLoad(config)
        self.excitation = OpenLoopExcitationModel(config)
        self.electrical_model = TerminalElectricalModel(config, self.excitation)
        self.governor = IsochronousGovernor(config) if config.CONTROL_MODE == "pi" else None
        self.model = GeneratorModel(config, self.load, self.governor, self.electrical_model)

    def _make_time_vector(self, start_s: float, end_s: float) -> FloatArray:
        """Create a deterministic time vector including the segment endpoint."""
        sample_count = int(math.floor((end_s - start_s) / self.config.DYNAMIC_SAMPLE_STEP_S)) + 1
        time_s = start_s + np.arange(sample_count, dtype=float) * self.config.DYNAMIC_SAMPLE_STEP_S
        if time_s[-1] < end_s:
            time_s = np.append(time_s, end_s)
        else:
            time_s[-1] = end_s
        return time_s.astype(float)

    def _solve_segment(
        self,
        start_s: float,
        end_s: float,
        initial_state: FloatArray,
    ):
        """Solve one continuous segment of the ODE model."""
        time_eval_s = self._make_time_vector(start_s, end_s)
        solution = solve_ivp(
            fun=self.model.state_derivatives,
            t_span=(start_s, end_s),
            y0=initial_state,
            t_eval=time_eval_s,
            dense_output=True,
            rtol=self.config.RELATIVE_TOLERANCE,
            atol=self.config.ABSOLUTE_TOLERANCE,
            max_step=self.config.SLOW_MAX_STEP_S,
        )
        if not solution.success:
            raise RuntimeError(f"ODE solver failed: {solution.message}")
        if solution.sol is None:
            raise RuntimeError("ODE solver did not return the dense solution required for waveform reconstruction.")
        return solution

    def run(self) -> SimulationResults:
        """Run the dynamic simulation with one segment per load plateau."""
        initial_terminal_quantities = self.electrical_model.solve_terminal_quantities(
            self.config.initial_resistance_ohm,
            self.config.FIELD_CURRENT_INITIAL_PU,
            omega_pu=1.0,
        )
        initial_state = np.array(
            [
                1.0,
                0.0,
                initial_terminal_quantities.electrical_power_pu,
                0.0,
                self.config.FIELD_CURRENT_INITIAL_PU,
            ],
            dtype=float,
        )

        segment_boundaries_s = [
            0.0,
            *self.config.load_step_times_s,
            self.config.SIMULATION_TIME_S,
        ]
        segment_solutions = []
        active_initial_state = initial_state
        for start_s, end_s in zip(segment_boundaries_s[:-1], segment_boundaries_s[1:]):
            segment_solution = self._solve_segment(start_s, end_s, active_initial_state)
            segment_solutions.append(segment_solution)
            active_initial_state = segment_solution.y[:, -1]

        time_parts = [segment_solutions[0].t]
        state_parts = [segment_solutions[0].y]
        for segment_solution in segment_solutions[1:]:
            time_parts.append(segment_solution.t[1:])
            state_parts.append(segment_solution.y[:, 1:])
        time_s = np.concatenate(time_parts).astype(float)
        state_matrix = np.column_stack(state_parts).astype(float)

        def sample_state(query_time_s: FloatArray) -> FloatArray:
            """Sample the dense solution at arbitrary times."""
            query = np.asarray(query_time_s, dtype=float)
            flat_query = np.atleast_1d(query).astype(float)
            sampled_state = np.empty((5, flat_query.size), dtype=float)
            for segment_index, segment_solution in enumerate(segment_solutions):
                start_s = segment_boundaries_s[segment_index]
                end_s = segment_boundaries_s[segment_index + 1]
                if segment_index == 0:
                    segment_mask = flat_query <= end_s
                else:
                    segment_mask = np.logical_and(flat_query > start_s, flat_query <= end_s)
                if np.any(segment_mask):
                    sampled_state[:, segment_mask] = segment_solution.sol(flat_query[segment_mask])
            return sampled_state

        omega_pu = state_matrix[0]
        integral_state = state_matrix[1]
        mechanical_power_pu = state_matrix[2]
        rotor_angle_rad = state_matrix[3]
        field_current_pu = state_matrix[4]
        load_resistance_ohm = np.asarray(self.load.resistance_at(time_s), dtype=float)
        terminal_quantities = self.electrical_model.terminal_quantities_at(
            load_resistance_ohm,
            field_current_pu,
            omega_pu,
        )
        electrical_power_pu = terminal_quantities["electrical_power_pu"]
        if self.governor is None:
            mechanical_power_reference_pu = mechanical_power_pu.copy()
        else:
            mechanical_power_reference_pu = np.asarray(
                self.governor.limited_reference_power_pu(omega_pu, integral_state),
                dtype=float,
            )

        return SimulationResults(
            config=self.config,
            time_s=time_s,
            omega_pu=omega_pu,
            integral_state=integral_state,
            mechanical_power_pu=mechanical_power_pu,
            rotor_angle_rad=rotor_angle_rad,
            electrical_power_pu=electrical_power_pu,
            load_resistance_ohm=load_resistance_ohm,
            mechanical_power_reference_pu=mechanical_power_reference_pu,
            field_current_pu=field_current_pu,
            internal_voltage_ll_rms=terminal_quantities["internal_voltage_ll_rms"],
            terminal_voltage_ll_rms=terminal_quantities["terminal_voltage_ll_rms"],
            terminal_voltage_phase_rms=terminal_quantities["terminal_voltage_phase_rms"],
            terminal_voltage_angle_rad=terminal_quantities["terminal_voltage_angle_rad"],
            load_current_phase_rms=terminal_quantities["load_current_phase_rms"],
            state_sampler=sample_state,
        )

    def waveform_dataframe(
        self,
        results: SimulationResults,
        start_s: float,
        end_s: float,
    ) -> pd.DataFrame:
        """Reconstruct three-phase voltages, currents, and instantaneous power."""
        if start_s < 0.0:
            raise ValueError("Waveform start time cannot be negative.")
        if end_s <= start_s:
            raise ValueError("Waveform end time must be greater than start time.")
        if end_s > self.config.SIMULATION_TIME_S:
            raise ValueError("Waveform end time cannot exceed the simulation time.")

        sample_count = int(math.floor((end_s - start_s) / self.config.WAVEFORM_SAMPLE_STEP_S)) + 1
        time_s = start_s + np.arange(sample_count, dtype=float) * self.config.WAVEFORM_SAMPLE_STEP_S
        if time_s[-1] < end_s:
            time_s = np.append(time_s, end_s)
        else:
            time_s[-1] = end_s

        state_matrix = results.state_sampler(time_s)
        theta_rad = state_matrix[3]
        field_current_pu = state_matrix[4]
        resistance_ohm = np.asarray(self.load.resistance_at(time_s), dtype=float)
        terminal_quantities = self.electrical_model.terminal_quantities_at(
            resistance_ohm,
            field_current_pu,
            state_matrix[0],
        )
        voltage_a_v, voltage_b_v, voltage_c_v = self.model.three_phase_voltages(
            theta_rad,
            terminal_quantities["terminal_voltage_phase_rms"],
            terminal_quantities["terminal_voltage_angle_rad"],
        )
        current_a_a, current_b_a, current_c_a = self.model.phase_currents(
            voltage_a_v,
            voltage_b_v,
            voltage_c_v,
            resistance_ohm,
        )
        total_power_w = (
            voltage_a_v * current_a_a
            + voltage_b_v * current_b_a
            + voltage_c_v * current_c_a
        )

        return pd.DataFrame(
            {
                "time_s": time_s,
                "theta_rad": theta_rad,
                "field_current_pu": field_current_pu,
                "resistance_ohm": resistance_ohm,
                "internal_voltage_ll_rms": terminal_quantities["internal_voltage_ll_rms"],
                "terminal_voltage_ll_rms": terminal_quantities["terminal_voltage_ll_rms"],
                "load_current_phase_rms": terminal_quantities["load_current_phase_rms"],
                "voltage_a_v": voltage_a_v,
                "voltage_b_v": voltage_b_v,
                "voltage_c_v": voltage_c_v,
                "current_a_a": current_a_a,
                "current_b_a": current_b_a,
                "current_c_a": current_c_a,
                "total_power_w": total_power_w,
                "total_power_pu": total_power_w / self.config.S_BASE_VA,
            }
        )
