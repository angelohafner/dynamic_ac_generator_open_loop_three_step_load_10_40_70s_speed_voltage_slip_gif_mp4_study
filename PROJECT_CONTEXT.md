# Project Context

## Current Goal

This project models a simplified isolated three-phase AC generator in open loop
for both speed and voltage. The present default case is intended to make the
rotor-reference slip visible over a long transient with three load changes.

Default selected simulation:

```text
CONTROL_MODE = "unregulated"
D = 0.0
speed loop = open loop
voltage loop = open loop
AVR = not modeled
field current = constant
mechanical input = constant
E = K_e If omega_pu
```

Initial operating point:

```text
f(0) = 60 Hz
omega_pu(0) = 1.0
V_terminal_LL_RMS(0) = 400 V
If(0) = 1.0 pu
initial load = 0.50 pu
Pm(0) = Pe(0)
```

Default load schedule:

```text
t = 0 s:    load = 0.50 pu
t = 10 s:   load = 0.80 pu
t = 40 s:   load = 0.35483294428516376 pu
t = 70 s:   load = 0.50 pu
t = 100 s:  end of simulation
```

The first load step makes the rotor slow down. The second load step reduces the
electrical load enough for the rotor to accelerate above 60 Hz. The third load
step restores the initial electrical load, so the final open-loop equilibrium
returns to 60 Hz.

The accumulated rotor-reference angle does not have to return to zero when the
frequency returns to 60 Hz. It is an integral of all previous frequency error,
so it preserves the history of the earlier lag and lead.

## Model Equations

State vector:

```text
x = [omega_pu, integral_state, mechanical_power_pu, rotor_angle_rad, field_current_pu]
```

Speed equation:

```text
d omega / dt = (Pm - Pe(omega) - D(omega - 1)) / (2H)
d theta / dt = omega_nominal omega
```

Open-loop excitation:

```text
E = K_e If omega_pu
dIf/dt = 0
```

Terminal electrical model:

```text
I_load = E_phase / (R_load + R_s + jX_s)
V_terminal_phase = I_load R_load
Pe = 3 |V_terminal_phase|^2 / R_load
```

Default simplified impedance:

```text
R_s = 0.02 pu
X_s = 0.50 pu
```

Open-loop equilibrium with `D = 0`:

```text
Pe(omega_final) = Pm
```

Open-loop equilibrium with `D > 0`:

```text
Pm - Pe(omega_final) - D(omega_final - 1) = 0
```

## Rotor-Reference Display

The physical 60 Hz reference and the rotor angle are:

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

Default animation settings:

```text
SLOW_MOTION_REFERENCE_FREQUENCY_HZ = 0.40
SLIP_ANIMATION_FRAME_COUNT = 1440
SLIP_ANIMATION_FPS = 24
```

The slip animation frames now start at `0 s` and end at `100 s`. This shows the
initial steady-state interval from `0 s` to `10 s`, then continues through the
load changes at `10 s`, `40 s`, and `70 s`. The chart x-axis uses absolute
simulation time, so the rendered load-change markers appear at those exact
times.

Important timing distinction:

```text
animated frame time window     = 0 s to 100 s
fixed time-chart x-axis        = 0 s to 100 s
load steps shown on chart      = 10 s, 40 s, 70 s
MP4 playback duration          = 60.125 s
MP4 frame rate                 = 24 fps
MP4 frame count                = 1443 frames
```

The MP4 duration is only the viewing duration of the rendered animation. It is
not the simulated physical time.

The `06_rotor_reference_slip` animation is a synchronized multi-panel figure:

```text
left upper panel: polar slow reference vector, rotor vector, and shaded lag sector
left lower panel: polar terminal phasor diagram with arrowhead fasors
right panels: six time charts arranged as 3 rows by 2 columns
right chart contents: frequency, terminal voltage, power balance, internal voltage, load resistance, accumulated lead
```

This animation is intentionally rendered only as:

```text
results/animations/06_rotor_reference_slip.mp4
```

No paired `06_rotor_reference_slip.gif` should be produced for this animation.

The shaded sector starts at 20 percent opacity and becomes more opaque as the
absolute accumulated lead or lag grows:

```text
alpha = min(0.80, 0.20 + 0.10 abs(lead_cycles))
```

Grid lines use 50 percent opacity. Auxiliary items such as load-step markers,
current-time markers, full background curves, the reference circle, and the lag
sector are intentionally hidden from legends. The left-column rotating-vector
and terminal-phasor panels use Matplotlib polar projection; fasors use arrows
instead of endpoint markers. The terminal phasor radial grid is fixed at `0.5`,
`1.0`, and `1.5` pu, and the rotor lag text uses an opaque white background.

## Module Responsibilities

- `config.py`: editable parameters, load schedule, base quantities, and validation
- `load.py`: balanced resistive load schedule and phase resistance calculation
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

## Run

Default open-loop selected case plus automatic comparison:

```powershell
python scripts/run_simulation.py
```

Fast run without animations:

```powershell
python scripts/run_simulation.py --skip-animations
```

Selected open-loop case directly with damping:

```powershell
python scripts/run_simulation.py --damping 2.0 --simulation-time 100
```

Optional PI speed-governed case:

```powershell
python scripts/run_simulation.py --control-mode pi
```

Regenerate only the corrected `06_rotor_reference_slip` MP4:

```powershell
python tools/regenerate_slip_animation.py
```

## Outputs

The full run writes:

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

The other default animations remain GIF files. The `06_rotor_reference_slip`
animation is MP4-only.

Important dynamic output columns:

```text
time_s
frequency_hz
omega_pu
frequency_error_hz
mechanical_power_pu
electrical_power_pu
mechanical_power_reference_pu
field_current_pu
internal_voltage_ll_rms
terminal_voltage_ll_rms
terminal_voltage_phase_rms
terminal_voltage_angle_rad
load_current_phase_rms
load_resistance_ohm
rotor_angle_rad
```

## Validation

The open-loop validation checks that:

- initial frequency is approximately 60 Hz
- initial mechanical and electrical powers are equal
- frequency initially decreases after the load increase
- mechanical power remains constant without a speed regulator
- initial terminal voltage is nominal
- field current remains constant without AVR
- terminal voltage drops after the first load increase
- final frequency reaches the theoretical open-loop equilibrium
- frequency increases after the second load reduction
- frequency decreases after the third load restoration
- phase voltages are displaced by approximately 120 degrees
- total instantaneous power varies smoothly for a balanced resistive load
- power and speed-derivative signs are consistent

## Handoff Notes For Codex

A new Codex session should:

1. Read `README.md` for the human-facing overview and commands.
2. Read this file for the concise engineering handoff.
3. Inspect `src/dynamic_ac_generator/config.py` before changing scenario values.
4. Use `pytest` for regression checks.
5. Use `python scripts/run_simulation.py` to regenerate outputs.
6. Use `python tools/regenerate_slip_animation.py` when only the long slip MP4
   needs to be rebuilt.
7. Keep `06_rotor_reference_slip` on absolute simulation time. The x-axis must
   show `10 s`, `40 s`, and `70 s` for the load changes. Do not convert this
   figure to time relative to the first load step.
8. Distinguish MP4 playback duration from physical simulation time: the current
   video plays for about `60.125 s`, while the time-chart x-axis is fixed from
   `0 s` to `100 s`.
9. Keep the load-resistance chart in the right-side time-series stack.
10. Keep the six right-side time charts arranged as 3 rows by 2 columns.
11. Keep the terminal phasor diagram directly below the rotating vectors.
12. Keep both left-column vector panels on Matplotlib polar axes, with
    arrowhead fasors instead of endpoint dots.
13. Keep the terminal phasor radial grid fixed at `0.5`, `1.0`, and `1.5`.
14. Keep the rotor lag `Lead` and `Full turns` text on an opaque white
    background.
15. Do not reintroduce `results/animations/06_rotor_reference_slip.gif`; this
    animation is intentionally MP4-only.

When changing load-step timing, update:

- `SimulationConfig.LOAD_STEP_TIME_S`
- `SimulationConfig.SECOND_LOAD_STEP_TIME_S`
- `SimulationConfig.THIRD_LOAD_STEP_TIME_S`
- `SimulationConfig.SIMULATION_TIME_S`
- tests in `tests/test_config.py`, `tests/test_load.py`, and `tests/test_animations.py`
- `README.md`
- `PROJECT_CONTEXT.md`
- regenerate `results/animations/06_rotor_reference_slip.mp4`

## Known Limitations

This simplified model does not include:

- AVR
- saturation
- detailed field-winding dynamics
- full dq-axis equations
- subtransient and transient reactances
- damper windings
- unbalanced-load effects
- shaft torsional dynamics
- protection or instability events for very low speed

The model is intended for didactic active-power, frequency, excitation,
voltage-drop, and rotor-reference slip behavior in a balanced isolated
generator.
