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
- static figures, CSV outputs, GIF animations, and an MP4 animation

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
initial load impedance = 0.50 pu angle -45 deg
```

The default load-impedance schedule is:

```text
t = 0 s:    Z_load = 0.50 pu angle -45 deg
t = 10 s:   Z_load = 0.80 pu angle -30 deg
t = 40 s:   Z_load = 0.20 pu angle -60 deg
t = 70 s:   Z_load = 0.50 pu angle -45 deg
t = 100 s:  end of simulation
```

Interpretation:

- `0 s` to `10 s`: steady at 60 Hz.
- After `10 s`: active electrical power drops and the rotor accelerates.
- After `40 s`: the rotor keeps accelerating in this selected open-loop case.
- After `70 s`: load impedance returns to the initial value, electrical power becomes larger than mechanical input at high speed, and the rotor decelerates toward 60 Hz.
- By `100 s`: the frequency is close to the final theoretical open-loop equilibrium.

The per-phase impedance magnitudes in ohms are obtained from
`Z_base = V_LL^2 / S_base = 1.6 ohm`:

```text
0.50 pu angle -45 deg -> |Z| = 0.80 ohm
0.80 pu angle -30 deg -> |Z| = 1.28 ohm
0.20 pu angle -60 deg -> |Z| = 0.32 ohm
0.50 pu angle -45 deg -> |Z| = 0.80 ohm
```

The accumulated rotor-reference angle does not necessarily return to zero when
frequency returns to 60 Hz. The angle is an integral of all previous frequency
error, so it keeps the history of earlier lead and lag:

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
SLIP_ANIMATION_FRAME_COUNT = 1440
SLIP_ANIMATION_FPS = 24
```

The slow-motion animation frames now start at `0 s` and end at `100 s`. This
shows the initial steady-state interval from `0 s` to `10 s` before the first
load step, then continues through the load changes at `10 s`, `40 s`, and
`70 s`.

The chart x-axis uses absolute simulation time. Therefore the load-change
markers appear at `10 s`, `40 s`, and `70 s` in the rendered MP4.
This is intentional: the MP4 playback length is not the same quantity as the
simulated time shown on the x-axis.

Current timing convention:

```text
animated frame time window                         = 0 s to 100 s
fixed time-chart x-axis                            = 0 s to 100 s
load-step markers shown on the chart             = 10 s, 40 s, 70 s
rendered video duration                          = 60.125 s
rendered video frame rate                        = 24 fps
rendered frame count                             = 1443 frames
```

The video duration is `frame_count / fps`. It only controls how slowly the
viewer sees the transient. The chart axis and the numerical results remain in
physical simulation seconds.

The synchronized `06_rotor_reference_slip` animation contains:

- a polar slow-motion reference vector and rotor vector
- a polar terminal phasor diagram below the rotating vectors
- a shaded rotor-reference lag sector
- six time-domain charts arranged as 3 rows by 2 columns:
  frequency, terminal voltage, mechanical/electrical power, internal voltage,
  load impedance magnitude/angle, and accumulated reference lead

The shaded sector starts at 20 percent opacity and becomes more opaque as the
absolute accumulated lead or lag grows:

```text
alpha = min(0.80, 0.20 + 0.10 abs(lead_cycles))
```

Grid lines use 50 percent opacity. Auxiliary items such as load-step markers,
current-time markers, full background curves, the reference circle, and the lag
sector are intentionally hidden from legends. The rotating-vector panel and the
terminal phasor panel both use Matplotlib polar axes. The terminal phasors are
drawn as arrows, not endpoint dots, so the arrowhead marks the fasor direction.
The terminal phasor panel uses the terminal voltage as the angular reference:
`V_terminal = |V_terminal| angle 0 deg`. The load-current fasor is drawn at
`-phi_load`, and the internal voltage fasor is drawn relative to that
terminal-voltage reference. The terminal phasor radial grid uses fixed circular
ticks at `0.5`, `1.0`, and `1.5` pu. The rotor lag text uses an opaque white
background so `Lead` and `Full turns` remain readable over the polar grid.

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
results/animations/*.gif
results/animations/06_rotor_reference_slip.mp4
```

Main animations:

```text
results/animations/01_unregulated_frequency_power_balance.gif
results/animations/02_rotor_three_phase_waveforms.gif
results/animations/03_unregulated_power_imbalance.gif
results/animations/04_unregulated_damping_comparison.gif
results/animations/05_open_loop_voltage_frequency.gif
results/animations/06_rotor_reference_slip.mp4
```

The `06_rotor_reference_slip.mp4` animation is the only default animation that
is rendered directly as MP4 without a GIF companion. It includes the load
impedance panel and the terminal phasor diagram.

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
- frequency acceleration, deceleration, and final return toward 60 Hz
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
- after `10 s`: frequency increases because active electrical power drops
- after `40 s`: frequency continues increasing in this selected open-loop case
- after `70 s`: frequency decreases toward 60 Hz because load impedance returns to the initial value
- by `100 s`: frequency is close to the final theoretical open-loop equilibrium

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
   plays for about `60.125 s`, while the physical simulation axis shown in the
   time charts is fixed from `0 s` to `100 s`.
9. Keep the `06_rotor_reference_slip` x-axis in absolute simulation time. Do
   not subtract `SimulationConfig.LOAD_STEP_TIME_S` from the frame times for
   this figure; otherwise the load markers visually become `0 s`, `30 s`, and
   `60 s` even though the simulation is configured for `10 s`, `40 s`, and
   `70 s`.
10. Keep the load-impedance panel on the absolute simulation-time axis, with
    `|Z|` on the left y-axis and impedance angle in degrees on the right y-axis.
11. Keep the terminal phasor diagram below the rotating vectors in the left
    column.
12. Keep both left-column vector panels on Matplotlib polar axes, and keep the
    six right-side time charts arranged as 3 rows by 2 columns.
13. Keep the terminal phasor radial grid fixed at `0.5`, `1.0`, and `1.5`.
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
