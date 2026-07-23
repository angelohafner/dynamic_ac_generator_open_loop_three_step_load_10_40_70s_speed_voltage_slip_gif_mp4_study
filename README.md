# Dynamic AC Generator Open-Loop Three-Step Load Study

This repository contains a didactic Python project for studying a simplified
isolated three-phase AC generator feeding a balanced star-connected complex-impedance
load. The default study is open loop for speed and open loop for voltage:

- no speed governor in the default case
- no AVR
- constant mechanical input
- constant field current
- generated internal voltage proportional to field current and rotor speed
- balanced three-phase impedance load with configurable magnitude and angle
- static figures, CSV outputs, and one default MP4 animation

The project was evolved from an exploratory notebook into a modular Python
package with tests, documentation, reproducible scripts, and generated
engineering visualizations.

## Current Default Scenario

The default simulation starts from an ideal operating point:

```text
f(0) = 60 Hz
omega_pu(0) = 1.0
V_terminal_LL_RMS(0) = 400 V
If(0) = 1.0 pu
Pm(0) = Pe(0)
initial load impedance = 1.4142135623730951 pu angle -45 deg
```

The default load-impedance schedule is chosen from desired active power at
nominal terminal voltage with fixed impedance angles:

```text
P_pu = cos(phi_load) / |Z_load|_pu
|Z_load|_pu = cos(phi_load) / P_pu
```

The resulting schedule is:

```text
t = 0 s:    P_target = 0.5 pu, Z_load = 1.4142135623730951 pu angle -45 deg
t = 10 s:   P_target = 1.0 pu, Z_load = 0.8660254037844387 pu angle -30 deg
t = 40 s:   P_target = 0.8 pu, Z_load = 0.625 pu angle -60 deg
t = 70 s:   P_target = 0.8 pu, Z_load = 0.625 pu angle +60 deg
t = 110 s:  end of simulation
```

Interpretation:

- `0 s` to `10 s`: steady at 60 Hz.
- After `10 s`: the nominal-voltage active-power target rises to `1.0 pu`,
  so electrical power is larger than the constant mechanical input and the
  rotor decelerates.
- After `40 s`: the nominal-voltage active-power target becomes `0.8 pu` at
  `-60 deg`; at the reached speed the generator keeps decelerating.
- After `70 s`: the magnitude stays at `0.625 pu`, but the angle changes to
  `+60 deg`; active power falls below the constant mechanical input and the
  rotor accelerates toward a higher open-loop equilibrium.
- By `110 s`: the numerical frequency is about `101.02 Hz`, still approaching
  the final theoretical open-loop equilibrium of about `103.28 Hz`; the
  estimated settling time is about `121.27 s`.

The per-phase impedance values in ohms are obtained from
`Z_base = V_LL^2 / S_base = 1.6 ohm`:

```text
1.4142135623730951 pu angle -45 deg -> 2.2627 ohm angle -45 deg -> 1.6000 - j1.6000 ohm
0.8660254037844387 pu angle -30 deg -> 1.3856 ohm angle -30 deg -> 1.2000 - j0.6928 ohm
0.625 pu angle -60 deg -> 1.0000 ohm angle -60 deg -> 0.5000 - j0.8660 ohm
0.625 pu angle +60 deg -> 1.0000 ohm angle +60 deg -> 0.5000 + j0.8660 ohm
```

The accumulated rotor-reference angle does not necessarily return to zero when
frequency reaches its final equilibrium. The angle is an integral of all
previous frequency error, so it keeps the history of earlier lead and lag:

```text
delta(t) = integral(2 pi (f_ref - f_rotor)) dt
```

## Main Equations

State vector:

```text
x = [omega_pu, integral_state, mechanical_power_pu, rotor_angle_rad, field_current_pu]
```

Open-loop excitation:

```text
E = K_e If omega_pu
dIf/dt = 0
```

Speed dynamics:

```text
d omega / dt = (Pm - Pe(omega) - D(omega - 1)) / (2H)
d theta / dt = omega_nominal omega
```

Balanced terminal phasor model:

```text
Z_load = |Z_load| angle phi_load
I_load = E_phase / (Z_load + R_s + jX_s)
V_terminal_phase = I_load Z_load
S_load = 3 V_terminal_phase conj(I_load)
Pe = Re(S_load) / S_base
Qe = Im(S_load) / S_base
```

Terminal phasor diagram convention:

```text
V_terminal = |V_terminal| angle 0 deg
I_load angle = -phi_load
E_internal angle = -angle(V_terminal in the internal-voltage reference frame)
```

Open-loop equilibrium with `D = 0`:

```text
Pe(omega_final) = Pm
```

Open-loop equilibrium with `D > 0`:

```text
Pm - Pe(omega_final) - D(omega_final - 1) = 0
```

## Rotor-Reference Animation Logic

The physical 60 Hz reference and rotor angle are:

```text
theta_ref_physical(t) = 2 pi F_NOM t
theta_rotor_physical(t) = integral(2 pi F_NOM omega_pu(t) dt)
delta(t) = theta_ref(t) - theta_rotor(t)
```

The long didactic animation uses a slow-motion display frequency so that both
vectors rotate counterclockwise visibly:

```text
theta_ref_visual(t) = 2 pi F_SLOW t
theta_rotor_visual(t) = integral(2 pi F_SLOW omega_pu(t) dt)
delta_visual(t) = theta_ref_visual(t) - theta_rotor_visual(t)
```

Default visual settings:

```text
SLOW_MOTION_REFERENCE_FREQUENCY_HZ = 0.40
SLIP_ANIMATION_FRAME_COUNT = 1680
SLIP_ANIMATION_FPS = 24
```

The slow-motion animation frames now start at `0 s` and end at `110 s`. This
shows the initial steady-state interval from `0 s` to `10 s` before the first
load step, then continues through the load changes at `10 s`, `40 s`, and
`70 s`.

The chart x-axis uses absolute simulation time. Therefore the load-change
markers appear at `10 s`, `40 s`, and `70 s` in the rendered MP4.
This is intentional: the MP4 playback length is not the same quantity as the
simulated time shown on the x-axis.

Current timing convention:

```text
animated frame time window                         = 0 s to 110 s
fixed time-chart x-axis                            = 0 s to 110 s
load-step markers shown on the chart             = 10 s, 40 s, 70 s
rendered video duration                          = 70.125 s
rendered video frame rate                        = 24 fps
rendered frame count                             = 1683 frames
maximum slow-reference angular step              = about 9.43 deg/frame
```

The video duration is `frame_count / fps`. It only controls how slowly the
viewer sees the transient. The chart axis and the numerical results remain in
physical simulation seconds.

The synchronized `06_rotor_reference_slip` animation contains:

- a polar slow-motion reference vector and rotor vector
- a polar terminal phasor diagram below the rotating vectors
- a shaded rotor-reference lag sector
- six time-domain chart groups arranged as 3 rows by 2 columns:
  frequency, terminal voltage, mechanical/electrical power, internal voltage,
  load impedance, and accumulated reference lead
- the load-impedance chart group is split into two stacked subplots sharing
  the same time axis: `|Z|`, `Re(Z)`, and `Im(Z)` on top, and impedance angle
  below

The shaded sector starts at 20 percent opacity and becomes more opaque as the
absolute accumulated lead or lag grows:

```text
alpha = min(0.80, 0.20 + 0.10 abs(lead_cycles))
```

Cartesian grid lines use 50 percent opacity. The polar panels show only angular
grid lines, spaced every 30 degrees, with circular radial grid lines removed.
Auxiliary items such as load-step markers,
current-time markers, full background curves, the reference circle, and the lag
sector are intentionally hidden from legends. The rotating-vector panel and the
terminal phasor panel both use Matplotlib polar axes. The terminal phasors are
drawn as arrows, not endpoint dots, so the arrowhead marks the fasor direction.
The terminal phasor panel uses the terminal voltage as the angular reference:
`V_terminal = |V_terminal| angle 0 deg`. The load-current fasor is drawn at
`-phi_load`, and the internal voltage fasor is drawn relative to that
terminal-voltage reference. The rotor lag text uses an opaque white background
so `Lead` and `Full turns` remain readable over the polar grid.

## Project Structure

```text
.
|-- README.md
|-- PROJECT_CONTEXT.md
|-- pyproject.toml
|-- requirements.txt
|-- scripts/
|   `-- run_simulation.py
|-- src/
|   `-- dynamic_ac_generator/
|       |-- animation.py
|       |-- cli.py
|       |-- config.py
|       |-- damping.py
|       |-- electrical.py
|       |-- excitation.py
|       |-- generator.py
|       |-- governor.py
|       |-- load.py
|       |-- plotting.py
|       |-- results.py
|       |-- runner.py
|       |-- simulation.py
|       `-- validation.py
|-- tests/
|-- tools/
`-- results/
    |-- animations/
    |-- figures/
    `-- *.csv
```

The `tools/` folder contains small maintenance utilities. The most important
one for the current generated artifacts is:

```text
tools/regenerate_slip_animation.py
```

It regenerates only `results/animations/06_rotor_reference_slip.mp4`. This
animation is intentionally MP4-only; the paired GIF is removed if it exists.

## Module Responsibilities

- `config.py`: editable parameters, load schedule, base quantities, and validation
- `load.py`: balanced complex-impedance load schedule and impedance calculation
- `excitation.py`: open-loop `E = K_e If omega_pu` excitation model
- `electrical.py`: balanced per-phase terminal phasor model
- `generator.py`: state derivatives and three-phase waveform reconstruction
- `simulation.py`: segmented ODE integration and dense state sampling
- `damping.py`: open-loop equilibrium theory and damping comparison
- `governor.py`: optional PI speed-governor model
- `results.py`: result container and summary tables
- `validation.py`: automatic engineering checks
- `plotting.py`: static Matplotlib figure generation
- `animation.py`: GIF and MP4 animation generation
- `runner.py`: complete workflow orchestration
- `cli.py`: command-line interface

## Installation

From the project root:

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```

For MP4 export, `ffmpeg` must be available on `PATH`. On this Windows machine,
`ffmpeg` was verified with:

```powershell
ffmpeg -version
```

## Run

Run the default open-loop scenario and generate CSVs, figures, GIFs, and MP4:

```powershell
python scripts/run_simulation.py
```

Run without animations for faster validation:

```powershell
python scripts/run_simulation.py --skip-animations
```

Run the optional PI speed-governed case:

```powershell
python scripts/run_simulation.py --control-mode pi
```

Run with a custom damping coefficient:

```powershell
python scripts/run_simulation.py --damping 2.0 --simulation-time 100
```

Regenerate only the corrected rotor-reference slip MP4:

```powershell
python tools/regenerate_slip_animation.py
```

## Outputs

The full default run writes:

```text
results/dynamic_generator_results.csv
results/dynamic_generator_summary.csv
results/validation_report.csv
results/damping_theory.csv
results/damping_comparison.csv
results/open_loop_equilibrium_curve.csv
results/figures/*.png
results/animations/06_rotor_reference_slip.mp4
```

Main animation:

```text
results/animations/06_rotor_reference_slip.mp4
```

The default animation workflow renders only
`06_rotor_reference_slip.mp4`. Older generated GIF artifacts were removed from
the repository because the current didactic view is the synchronized multi-panel
MP4. Historical GIF helper functions still exist in `animation.py` for manual
experiments, but they are not part of the default run.

Important static figures:

```text
results/figures/01_generator_frequency.png
results/figures/03_mechanical_and_electrical_power.png
results/figures/04_load_impedance.png
results/figures/17_open_loop_internal_terminal_voltage.png
results/figures/18_open_loop_load_current_field_current.png
results/figures/19_open_loop_power_speed_equilibrium.png
```

Important result columns:

```text
time_s
frequency_hz
omega_pu
frequency_error_hz
mechanical_power_pu
electrical_power_pu
reactive_power_pu
mechanical_power_reference_pu
field_current_pu
internal_voltage_ll_rms
terminal_voltage_ll_rms
terminal_voltage_phase_rms
terminal_voltage_angle_rad
load_current_phase_rms
load_current_angle_rad
load_impedance_real_ohm
load_impedance_imag_ohm
load_impedance_magnitude_ohm
load_impedance_angle_deg
rotor_angle_rad
```

## Validation

Run the automated tests:

```powershell
pytest
```

The tests cover:

- nominal initial operating point
- load schedule at `10 s`, `40 s`, and `70 s`
- balanced complex-impedance load calculations
- terminal-voltage-reference phasor convention
- open-loop field-current behavior
- generated voltage proportional to field current and speed
- terminal-voltage drop after the first impedance change
- frequency deceleration after the first two load changes and final acceleration toward the high-frequency open-loop equilibrium
- open-loop equilibrium theory
- damping comparison outputs
- waveform consistency
- fixed legend placement
- hidden auxiliary legend items
- 50 percent grid opacity
- LaTeX rotor-axis labels
- MP4-only export hook for the long rotor-reference slip animation

## Current Verified Behavior

After the default run, the expected qualitative behavior is:

- `0 s` to `10 s`: steady at 60 Hz
- after `10 s`: frequency decreases because the nominal-voltage active-power target rises to `1.0 pu`
- after `40 s`: frequency keeps decreasing because electrical power remains larger than mechanical input at the reached speed
- after `70 s`: frequency increases because the final `0.625 pu angle +60 deg` load consumes less active power than the constant mechanical input at the reached speed
- by `110 s`: frequency reaches about `101.02 Hz`, approaching the final theoretical open-loop equilibrium of about `103.28 Hz`

## Notes For Codex

This repository is intended to be self-contained. A new Codex session should:

1. Read `README.md` first for the human-facing overview and commands.
2. Read `PROJECT_CONTEXT.md` for concise engineering state and handoff details.
3. Inspect `src/dynamic_ac_generator/config.py` before changing scenario values.
4. Use `pytest` for regression checks.
5. Use `python scripts/run_simulation.py` to regenerate all outputs.
6. Use `python tools/regenerate_slip_animation.py` when only the long
   rotor-reference slip MP4 needs to be rebuilt.
7. Remember that `results/animations/06_rotor_reference_slip.mp4` is
   intentionally MP4-only. Do not reintroduce a paired
   `results/animations/06_rotor_reference_slip.gif` output for this animation.
8. Do not interpret the MP4 duration as simulated time. The video currently
   plays for about `70.125 s`, while the physical simulation axis shown in the
   time charts is fixed from `0 s` to `110 s`.
9. Keep the `06_rotor_reference_slip` x-axis in absolute simulation time. Do
   not subtract `SimulationConfig.LOAD_STEP_TIME_S` from the frame times for
   this figure; otherwise the load markers visually become `0 s`, `30 s`, and
   `60 s` even though the simulation is configured for `10 s`, `40 s`, and
   `70 s`.
10. Keep the load-impedance panel on the absolute simulation-time axis, split
    into two stacked subplots sharing time: `|Z|`, `Re(Z)`, and `Im(Z)` on top,
    and impedance angle below.
11. Keep the terminal phasor diagram below the rotating vectors in the left
    column.
12. Keep both left-column vector panels on Matplotlib polar axes, and keep the
    six right-side time charts arranged as 3 rows by 2 columns.
13. Keep both polar panels with angular grid lines only, spaced every 30
    degrees; do not reintroduce circular radial grid lines.
14. Keep the rotor lag `Lead` and `Full turns` text on an opaque white
    background.
15. Keep the terminal phasor diagram referenced to terminal voltage:
    `V_terminal = |V_terminal| angle 0 deg`; draw `I_load` at `-phi_load`
    and draw `E_internal` relative to that reference.

When changing load-step timing, update:

- `SimulationConfig.LOAD_STEP_TIME_S`
- `SimulationConfig.SECOND_LOAD_STEP_TIME_S`
- `SimulationConfig.THIRD_LOAD_STEP_TIME_S`
- `SimulationConfig.SIMULATION_TIME_S`
- tests in `tests/test_config.py`, `tests/test_load.py`, and `tests/test_animations.py`
- this README
- `PROJECT_CONTEXT.md`
- regenerate `results/animations/06_rotor_reference_slip.mp4`

## Model Limitations

This is a teaching model. It does not include:

- AVR
- saturation
- detailed field-winding dynamics
- full dq-axis equations
- subtransient and transient reactances
- damper windings
- unbalanced loads
- magnetic saturation
- shaft torsional dynamics
- protection or instability events for extreme low-speed operation

The model is useful for didactic active-power, frequency, excitation,
voltage-drop, reactive-power, and rotor-reference slip behavior in a balanced isolated
generator.
