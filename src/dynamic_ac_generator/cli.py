"""Command-line interface for the dynamic AC generator simulation."""

from __future__ import annotations

import argparse
from pathlib import Path

from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.runner import run_complete_simulation


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Run a simplified dynamic AC generator simulation with a balanced resistive load.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results"),
        help="Directory where CSV files and figure PNG files are saved.",
    )
    parser.add_argument(
        "--skip-animations",
        action="store_true",
        help="Skip GIF animation generation for a faster run.",
    )
    parser.add_argument(
        "--control-mode",
        choices=["unregulated", "pi"],
        default="unregulated",
        help="Speed-control mode used by the simulation.",
    )
    parser.add_argument(
        "--damping",
        type=float,
        default=None,
        help="Damping coefficient D used by the selected simulation case.",
    )
    parser.add_argument(
        "--simulation-time",
        type=float,
        default=None,
        help="Simulation time in seconds for the selected simulation case.",
    )
    parser.add_argument(
        "--damped-comparison-d",
        type=float,
        default=None,
        help="Damping coefficient used by the automatic D=0 versus D>0 comparison.",
    )
    return parser


def main() -> None:
    """Run the full simulation workflow from the command line."""
    parser = build_parser()
    args = parser.parse_args()
    config_kwargs = {"CONTROL_MODE": args.control_mode}
    if args.damping is not None:
        config_kwargs["D"] = args.damping
    if args.simulation_time is not None:
        config_kwargs["SIMULATION_TIME_S"] = args.simulation_time
    if args.damped_comparison_d is not None:
        config_kwargs["DAMPED_COMPARISON_D"] = args.damped_comparison_d

    artifacts = run_complete_simulation(
        SimulationConfig(**config_kwargs),
        args.output_dir,
        save_animations=not args.skip_animations,
    )

    validation_counts = artifacts.validation_report["status"].value_counts().to_dict()
    minimum_frequency_hz = float(artifacts.results.frequency_hz.min())
    final_frequency_hz = float(artifacts.results.frequency_hz[-1])

    print("Dynamic AC generator simulation finished.")
    print(f"Control mode: {artifacts.results.config.CONTROL_MODE}")
    print(f"Damping coefficient D: {artifacts.results.config.D:.6f}")
    print(f"Minimum frequency: {minimum_frequency_hz:.6f} Hz")
    print(f"Final frequency: {final_frequency_hz:.6f} Hz")
    print(f"Validation status counts: {validation_counts}")
    print(f"Saved dynamic results to: {artifacts.dynamic_results_path}")
    print(f"Saved summary results to: {artifacts.summary_results_path}")
    print(f"Saved validation report to: {artifacts.validation_results_path}")
    if artifacts.damping_theory_path is not None:
        print(f"Saved damping theory to: {artifacts.damping_theory_path}")
    if artifacts.damping_comparison_path is not None:
        print(f"Saved damping comparison to: {artifacts.damping_comparison_path}")
    if artifacts.open_loop_equilibrium_curve_path is not None:
        print(f"Saved open-loop equilibrium curve to: {artifacts.open_loop_equilibrium_curve_path}")
    print(f"Saved {len(artifacts.figure_paths)} figures to: {artifacts.figures_dir}")
    print(f"Saved {len(artifacts.animation_paths)} animations to: {artifacts.animations_dir}")


if __name__ == "__main__":
    main()
