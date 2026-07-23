"""High-level execution workflow for the dynamic generator project."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from dynamic_ac_generator.animation import generate_all_animations
from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.damping import (
    build_damping_comparison,
    build_damping_theory_table,
    build_open_loop_equilibrium_curve,
)
from dynamic_ac_generator.plotting import (
    generate_all_figures,
    generate_damping_comparison_figures,
    generate_open_loop_equilibrium_curve_figure,
)
from dynamic_ac_generator.results import SimulationResults, build_summary_table
from dynamic_ac_generator.simulation import DynamicSimulation
from dynamic_ac_generator.validation import build_validation_report


@dataclass(frozen=True)
class RunArtifacts:
    """Paths and tables produced by a complete simulation run."""

    output_dir: Path
    figures_dir: Path
    animations_dir: Path
    dynamic_results_path: Path
    summary_results_path: Path
    validation_results_path: Path
    damping_theory_path: Path | None
    damping_comparison_path: Path | None
    open_loop_equilibrium_curve_path: Path | None
    figure_paths: list[Path]
    animation_paths: list[Path]
    results: SimulationResults
    summary_table: pd.DataFrame
    validation_report: pd.DataFrame
    damping_theory_table: pd.DataFrame | None
    damping_comparison_table: pd.DataFrame | None
    open_loop_equilibrium_curve: pd.DataFrame | None


def run_complete_simulation(
    config: SimulationConfig | None = None,
    output_dir: Path | str = Path("results"),
    save_animations: bool = True,
) -> RunArtifacts:
    """Run the selected control mode, tables, validations, figures, and optional animations."""
    active_config = config if config is not None else SimulationConfig()
    output_path = Path(output_dir)
    figures_path = output_path / "figures"
    animations_path = output_path / "animations"
    output_path.mkdir(parents=True, exist_ok=True)
    figures_path.mkdir(parents=True, exist_ok=True)
    for old_figure_path in figures_path.glob("*.png"):
        old_figure_path.unlink()
    if save_animations:
        animations_path.mkdir(parents=True, exist_ok=True)
        for old_animation_path in animations_path.glob("*.gif"):
            old_animation_path.unlink()
        for old_animation_path in animations_path.glob("*.mp4"):
            old_animation_path.unlink()

    simulation = DynamicSimulation(active_config)
    results = simulation.run()

    before_start_s = active_config.LOAD_STEP_TIME_S - active_config.WAVEFORM_WINDOW_S
    before_end_s = active_config.LOAD_STEP_TIME_S
    after_start_s = active_config.LOAD_STEP_TIME_S
    after_end_s = active_config.LOAD_STEP_TIME_S + active_config.WAVEFORM_WINDOW_S
    power_window_start_s = active_config.LOAD_STEP_TIME_S - 0.03
    power_window_end_s = active_config.LOAD_STEP_TIME_S + 0.09

    waveforms_before = simulation.waveform_dataframe(results, before_start_s, before_end_s)
    waveforms_after = simulation.waveform_dataframe(results, after_start_s, after_end_s)
    waveforms_power = simulation.waveform_dataframe(results, power_window_start_s, power_window_end_s)

    summary_table = build_summary_table(results)
    validation_report = build_validation_report(results, waveforms_after)

    figure_paths = generate_all_figures(
        results,
        waveforms_before,
        waveforms_after,
        waveforms_power,
        figures_path,
    )
    damping_theory_table: pd.DataFrame | None = None
    damping_comparison_table: pd.DataFrame | None = None
    damping_theory_path: Path | None = None
    damping_comparison_path: Path | None = None
    open_loop_equilibrium_curve_path: Path | None = None
    open_loop_equilibrium_curve: pd.DataFrame | None = None
    damping_comparison = None
    if active_config.CONTROL_MODE == "unregulated":
        damping_comparison = build_damping_comparison(active_config)
        open_loop_equilibrium_curve = build_open_loop_equilibrium_curve(active_config)
        damping_theory_table = build_damping_theory_table(
            active_config,
            damping_comparison.damped_results.config,
        )
        damping_comparison_table = damping_comparison.table
        figure_paths = figure_paths + generate_damping_comparison_figures(
            damping_comparison,
            figures_path,
        )
        figure_paths.append(
            generate_open_loop_equilibrium_curve_figure(
                active_config,
                open_loop_equilibrium_curve,
                figures_path,
            )
        )

    animation_paths = generate_all_animations(simulation, results, animations_path) if save_animations else []

    dynamic_results_path = output_path / "dynamic_generator_results.csv"
    summary_results_path = output_path / "dynamic_generator_summary.csv"
    validation_results_path = output_path / "validation_report.csv"
    damping_theory_path = output_path / "damping_theory.csv" if damping_theory_table is not None else None
    damping_comparison_path = output_path / "damping_comparison.csv" if damping_comparison_table is not None else None
    open_loop_equilibrium_curve_path = (
        output_path / "open_loop_equilibrium_curve.csv"
        if open_loop_equilibrium_curve is not None
        else None
    )
    stale_comparison_path = output_path / "governor_comparison.csv"
    if stale_comparison_path.exists():
        stale_comparison_path.unlink()
    stale_comparison_figure_path = figures_path / "14_frequency_response_comparison.png"
    if stale_comparison_figure_path.exists():
        stale_comparison_figure_path.unlink()

    results.to_dataframe().to_csv(dynamic_results_path, index=False)
    summary_table.to_csv(summary_results_path, index=False)
    validation_report.to_csv(validation_results_path, index=False)
    if damping_theory_table is not None and damping_theory_path is not None:
        damping_theory_table.to_csv(damping_theory_path, index=False)
    if damping_comparison_table is not None and damping_comparison_path is not None:
        damping_comparison_table.to_csv(damping_comparison_path, index=False)
    if open_loop_equilibrium_curve is not None and open_loop_equilibrium_curve_path is not None:
        open_loop_equilibrium_curve.to_csv(open_loop_equilibrium_curve_path, index=False)

    return RunArtifacts(
        output_dir=output_path,
        figures_dir=figures_path,
        animations_dir=animations_path,
        dynamic_results_path=dynamic_results_path,
        summary_results_path=summary_results_path,
        validation_results_path=validation_results_path,
        damping_theory_path=damping_theory_path,
        damping_comparison_path=damping_comparison_path,
        open_loop_equilibrium_curve_path=open_loop_equilibrium_curve_path,
        figure_paths=figure_paths,
        animation_paths=animation_paths,
        results=results,
        summary_table=summary_table,
        validation_report=validation_report,
        damping_theory_table=damping_theory_table,
        damping_comparison_table=damping_comparison_table,
        open_loop_equilibrium_curve=open_loop_equilibrium_curve,
    )
