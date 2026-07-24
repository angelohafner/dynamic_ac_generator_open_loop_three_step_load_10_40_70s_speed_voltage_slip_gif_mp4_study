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
LOAD_MODEL = "parallel_admittance"
```

Initial operating point:

```text
f(0) = 60 Hz
omega_pu(0) = 1.0
V_terminal_LL_RMS(0) = 400 V
If(0) = 1.0 pu
initial load admittance = 0.5 + j0.5 pu
initial equivalent load impedance = 1.4142135623730951 pu angle -45 deg
Pm(0) = Pe(0)
```

Default load schedule, using the parallel-admittance model:

```text
S_load,nom = P + jQ
Q = P tan(phi_load)
Y_load = conj(S_load,nom) = P - jQ
Z_equivalent = 1 / Y_load
```

Resulting schedule:

| Time | Configured load | Parallel admittance `Y_load` | Equivalent impedance `Z_equivalent` |
|---:|---:|---:|---:|
| `0 s` | `P = 0.5 pu`, `phi = -45 deg` | `0.5 + j0.5 pu` | `1.4142135624 pu angle -45 deg` |
| `10 s` | `P = 1.0 pu`, `phi = -30 deg` | `1.0 + j0.5773502692 pu` | `0.8660254038 pu angle -30 deg` |
| `40 s` | `P = 0.6 pu`, `phi = -10 deg` | `0.6 + j0.1057961884 pu` | `1.6413462550 pu angle -10 deg` |
| `70 s` | `P = 0.6 pu`, `phi = +10 deg` | `0.6 - j0.1057961884 pu` | `1.6413462550 pu angle +10 deg` |
| `110 s` | end of simulation | unchanged from `70 s` | unchanged from `70 s` |

Sign convention:

```text
phi_load < 0 deg -> Q < 0, capacitive load, B > 0
phi_load > 0 deg -> Q > 0, inductive load, B < 0
```

The first load step raises the nominal-voltage active-power target to
`1.0 pu`, so active electrical power is larger than the constant mechanical
input and the rotor decelerates. The second load step changes the target to
`0.6 pu` at `-10 deg`; at the reached speed, active electrical power becomes
lower than mechanical input, so the rotor accelerates toward about `68.57 Hz`.
The third load step keeps `P = 0.6 pu` but changes the angle to `+10 deg`;
the inductive angle lowers the nominal-speed active-power coefficient and the
rotor accelerates toward about `75.40 Hz`.

With `Z_base = V_LL^2 / S_base = 1.6 ohm`, the four per-phase equivalent
impedance magnitudes are `2.2627 ohm`, `1.3856 ohm`, `2.6262 ohm`, and
`2.6262 ohm`.
The rectangular values are approximately `1.6000 - j1.6000 ohm`,
`1.2000 - j0.6928 ohm`, `2.5863 - j0.4560 ohm`, and
`2.5863 + j0.4560 ohm`.

The current regenerated run reaches about `75.36 Hz` at `110 s`, while the
open-loop equilibrium theory predicts about `75.40 Hz`. The estimated settling
time is about `89.72 s`, so the validation report currently contains only PASS
rows for the default run.

The accumulated rotor-reference angle does not have to return to zero when the
frequency reaches the final equilibrium. It is an integral of all previous
frequency error, so it preserves the history of the earlier lag and lead.

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

Default terminal electrical model:

```text
S_load,nom = P + jQ
Q = P tan(phi_load)
Y_load = P - jQ
Z_equivalent = 1 / Y_load
I_load = E_phase / (Z_equivalent + R_s + jX_s)
V_terminal_phase = I_load Z_equivalent
S_load = 3 V_terminal_phase conj(I_load)
Pe = Re(S_load) / S_base
Qe = Im(S_load) / S_base
```

Compatibility mode:

```text
LOAD_MODEL = "series_impedance"
Z_load = |Z_load| angle phi_load
Y_load = 1 / Z_load
```

Terminal phasor diagram convention:

```text
V_terminal = |V_terminal| angle 0 deg
I_load angle = -phi_load
E_internal angle = -angle(V_terminal in the internal-voltage reference frame)
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
SLIP_ANIMATION_FRAME_COUNT = 1680
SLIP_ANIMATION_FPS = 24
```

The slip animation frames now start at `0 s` and end at `110 s`. This shows the
initial steady-state interval from `0 s` to `10 s`, then continues through the
load changes at `10 s`, `40 s`, and `70 s`. The chart x-axis uses absolute
simulation time, so the rendered load-change markers appear at those exact
times.

Important timing distinction:

```text
animated frame time window     = 0 s to 110 s
fixed time-chart x-axis        = 0 s to 110 s
load steps shown on chart      = 10 s, 40 s, 70 s
MP4 playback duration          = 70.125 s
MP4 frame rate                 = 24 fps
MP4 frame count                = 1683 frames
maximum visual angular step    = about 9.43 deg/frame
```

The MP4 duration is only the viewing duration of the rendered animation. It is
not the simulated physical time.

The `06_rotor_reference_slip` animation is a synchronized multi-panel figure:

```text
left upper panel: polar slow reference vector, rotor vector, and shaded lag sector
left lower panel: polar terminal phasor diagram with arrowhead fasors
right panels: six time charts arranged as 3 rows by 2 columns
right chart contents: frequency, terminal voltage, power balance, internal voltage, load admittance magnitude/real/imaginary/angle, accumulated lead
```

This animation is intentionally rendered only as:

```text
results/animations/06_rotor_reference_slip.mp4
D:/dynamic_ac_generator_open_loop_three_step_load_10_40_70s_speed_voltage_slip_gif_mp4_study/results/animations/06_rotor_reference_slip.mp4
```

No paired `06_rotor_reference_slip.gif` should be produced for this animation.

The shaded sector starts at 20 percent opacity and becomes more opaque as the
absolute accumulated lead or lag grows:

```text
alpha = min(0.80, 0.20 + 0.10 abs(lead_cycles))
```

Cartesian grid lines use 50 percent opacity. The polar panels show only angular
grid lines, spaced every 30 degrees, with circular radial grid lines removed.
Auxiliary items such as load-step markers, current-time markers, full
background curves, the reference circle, and the lag sector are intentionally
hidden from legends. The left-column rotating-vector and terminal-phasor panels
use Matplotlib polar projection; fasors use arrows instead of endpoint markers.
The terminal phasor diagram uses terminal voltage as the angular reference, so
`V_terminal` is drawn at `0 deg`; `I_load` is drawn at `-phi_load`, and
`E_internal` is drawn relative to that terminal-voltage reference. The
load-admittance panel is split into two stacked subplots sharing absolute
simulation time: `|Y|`, `G`, and `B` in pu on top, and admittance angle in
degrees below. In `series_impedance` mode, the same panel may show `|Z|`,
`Re(Z)`, `Im(Z)`, and impedance angle instead. The rotor lag text uses an
opaque white background.

## Module Responsibilities

- `config.py`: editable parameters, load schedule, base quantities, and validation
- `load.py`: balanced load schedule, parallel admittance, and equivalent impedance calculation
- `excitation.py`: open-loop `E = K_e If omega_pu` excitation model
- `electrical.py`: balanced per-phase terminal phasor model
- `generator.py`: state derivatives and three-phase waveform reconstruction
- `simulation.py`: segmented ODE integration and dense state sampling
- `damping.py`: open-loop equilibrium theory and damping comparison
- `governor.py`: optional PI speed-governor model
- `results.py`: result container and summary tables
- `validation.py`: automatic engineering checks
- `plotting.py`: static Matplotlib figure generation
- `animation.py`: MP4 animation workflow and legacy helper animation functions
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
results/animations/06_rotor_reference_slip.mp4
```

The default animation workflow renders only `06_rotor_reference_slip.mp4`.
Older GIF artifacts were removed because they are no longer part of the current
synchronized multi-panel view.

Important dynamic output columns:

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
load_admittance_real_pu
load_admittance_imag_pu
load_admittance_magnitude_pu
load_admittance_angle_deg
load_conductance_pu
load_susceptance_pu
rotor_angle_rad
```

## Validation

The open-loop validation checks that:

- initial frequency is approximately 60 Hz
- initial mechanical and electrical powers are equal
- frequency initially follows the first load-change power imbalance
- mechanical power remains constant without a speed regulator
- initial terminal voltage is nominal
- field current remains constant without AVR
- terminal voltage drops after the first load change
- final frequency reaches the theoretical open-loop equilibrium
- frequency response follows the second load-change power imbalance
- frequency response follows the third load-change power imbalance
- terminal phasors are drawn relative to `V_terminal = |V_terminal| angle 0 deg`
- phase voltages are displaced by approximately 120 degrees
- total instantaneous power varies smoothly for a balanced load
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
   video plays for about `70.125 s`, while the time-chart x-axis is fixed from
   `0 s` to `110 s`.
9. Keep the default load-admittance chart in the right-side time-series stack,
   split into two stacked subplots sharing the same time axis: `|Y|`, `G`, and
   `B` on top, and admittance angle below. Keep the fallback impedance panel
   available for `LOAD_MODEL = "series_impedance"`.
10. Keep the six right-side time charts arranged as 3 rows by 2 columns.
11. Keep the terminal phasor diagram directly below the rotating vectors.
12. Keep both left-column vector panels on Matplotlib polar axes, with
    arrowhead fasors instead of endpoint dots.
13. Keep both polar panels with angular grid lines only, spaced every 30
    degrees; do not reintroduce circular radial grid lines.
14. Keep the rotor lag `Lead` and `Full turns` text on an opaque white
    background.
15. Do not reintroduce `results/animations/06_rotor_reference_slip.gif`; this
    animation is intentionally MP4-only.
16. Keep the terminal phasor panel referenced to terminal voltage:
    `V_terminal = |V_terminal| angle 0 deg`, with `I_load` at `-phi_load`.

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
