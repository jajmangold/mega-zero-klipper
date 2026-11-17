# Orca Slicer presets

Three presets, all needed together:

| file | select as |
|---|---|
| `MegaZero Klipper 0.4.json` | printer |
| `PETG @MegaZero 0.4.json` | filament |
| `0.20mm MegaZero (process).json` | process |

They live in `%APPDATA%\OrcaSlicer\user\default\{machine,filament,process}\`.

## Install

**Duplicate an existing preset in the Orca UI and edit that**, rather than
dropping these files in directly. Orca then authors the preset correctly and you
only change values. See the warnings below for why.

The process preset here is a copy of `0.20mm Standard @MyKlipper` with the
machine-specific values changed.

## What's set and why

**Acceleration — the important one.** Orca's Klipper flavour emits
`SET_VELOCITY_LIMIT ACCEL=` into the gcode, which **overrides `max_accel` at
runtime and is NOT clamped by it**. The config value is a default, not a
ceiling. Stock profiles asked for 5000–7000 mm/s² — that was the bug. These
numbers are the opposite case: deliberately raised, after measuring.

```
default_acceleration        2000
outer_wall_acceleration     1000
inner_wall_acceleration     2000
sparse_infill_acceleration  2500
travel_acceleration         3000
initial_layer_acceleration   500
```

**Why 500 was costing so much.** Acceleration, not velocity, is the real limit.
At 500 mm/s², reaching 70 mm/s takes `70²/(2×500)` = **4.9 mm** of runway plus
the same to stop — so any move under ~10 mm never reached its nominal speed, and
the speed settings were largely decorative. Travel was worse: 150 mm/s needed
22.5 mm, longer than most travels on a 105 mm-wide print area.

> **The process preset is NOT enough — the MACHINE preset caps it.** Orca clamps
> every process acceleration to `machine_max_acceleration_*` in the machine
> preset, which were all still at **500**. Raising the process values alone
> changes nothing; Orca just silently caps them back down. It does say so, in a
> dismissable warning box: *"The acceleration setting exceeds the printer's
> maximum acceleration (machine_max_acceleration_extruding). Orca will
> automatically cap the acceleration speed…"*
>
> Set `machine_max_acceleration_x`, `_y`, `_extruding`, `_travel` and
> `_retracting` to **3000** (each is a 2-entry array — normal and silent mode,
> both need changing). Leave `machine_max_acceleration_z` at 100: those are lead
> screws.

**Measured, not guessed** — [`tools/acceltower.py`](../tools/acceltower.py)
prints a 50 × 50 single-wall square, 25 mm tall, in 5 mm bands at 500 / 1000 /
1500 / 2000 / 3000 mm/s², at a constant 80 mm/s so only acceleration varies.
Result: **no visible difference between any of the bands** — no ringing after
corners, no layer shift, square top and bottom. The ceiling was never found; the
numbers above are conservative against an untested limit.

Verify the bands actually changed before trusting such a test — a rejected
`SET_VELOCITY_LIMIT` would print the whole tower at one value:

```
SET_VELOCITY_LIMIT ACCEL=3000 ACCEL_TO_DECEL=1500
# then query toolhead.max_accel - it should read 3000
```

**There is still no input shaper and no accelerometer.** That it rings so little
at 3000 is a property of this frame, not a general result.

**Speeds.** PETG through a 0.4 nozzle at 0.2 × 0.42 moves 0.084 mm² of
cross-section, so 100 mm/s = **8.4 mm³/s** — about all a 40 W V6 clone will melt.
Past ~100 mm/s it would simply under-extrude, so `filament_max_volumetric_speed`
is set to **9** as a backstop. Infill runs 100 mm/s; stock asked for 200.

**`minimum_cruise_ratio` is 0.5**, which forces half of every move to be at
cruise speed and therefore blunts short moves. Lowering it to ~0.3 is the next
available gain, untested here.

**`printable_area` is the USABLE region, not the machine's reach:**

```
"printable_area": [ "15x45", "120x45", "120x195", "15x195" ]
```

It started as `220x220`, was corrected to the real travel `185x220` — and that
was still wrong, because *reachable* is not *printable*. With `x_offset -55` the
probe only covers bed X 0–130, so anything outside X 15–120 / Y 45–195 prints on
bed Klipper has never measured.

Declaring the full rectangle let Orca drop a part at **Y30**, 15 mm outside the
mesh and ~5 mm from the plate's front edge, on a 50 × 2 mm footprint. That alone
ruins a first layer no matter what `z_offset` is, and it looks exactly like a Z
problem. With the usable region declared, Orca centres on **(67.5, 120)** and
cannot place a part there at all.

The cost is giving up X120–185, which the nozzle *can* reach. That area is
unmeshed and unmeasurable, so it was never reliably printable anyway.

[`tools/bedmap.py`](../tools/bedmap.py) prints a labelled grid over the usable
area — boundary, gridlines every 20 mm in X and 30 mm in Y, a corner marker at
(15,45), and doubled reference lines at X60 and Y120. Photograph the result to
read any physical feature off in bed coordinates. It settled the COMGROW logo
question in one print: the logo is **entirely in front of Y45**.

**Retraction 0.8 mm @ 35** — direct drive. Note Orca emits its own `G1 E`
retractions and **ignores `[firmware_retraction]` entirely**, so the printer's
value does not apply to sliced prints. The two are independent and both need
setting.

**Supports: normal/grid, not tree.** Tree branches are thin and unbraced, PETG
is sticky rather than brittle, and the nozzle drags the tips.

**No slicer-side pressure advance.** Klipper applies it in firmware; setting it
here too double-applies.

## Traps

**Orca silently reverts preset edits made while it is running.** It writes
presets back from its in-memory copy on exit. **Close Orca before editing any
file under `user/default/`.** The same acceleration value was reverted three
separate times before this was noticed.

**Hand-written presets are rejected silently** if they lack the variant arrays —
`print_extruder_variant` on a process preset, `filament_extruder_variant` on a
filament preset. The preset simply never appears in the dropdown, with no error.
Value arrays must also match the variant count (six temperature entries, not
one).

**To find a valid `inherits` name**, slice anything and read
`printer_settings_id` / `filament_settings_id` / `print_settings_id` from the
gcode footer.

## Verify before a long print

```bash
grep -o 'ACCEL=[0-9]*' file.gcode | sort | uniq -c
grep -m1 'retraction_length' file.gcode
```

Accel should read **3000 and below**, with 2000/2500 common. If 5000 or 7000
appear, the process preset didn't apply — that is the stock profile leaking
through, and there is no point running the print.

## Connection

`host_type: octoprint`, pointing at the container's LAN address on port 80.
Moonraker's `[octoprint_compat]` provides the OctoPrint-compatible upload API
behind nginx.

## Machine-specific values to change

- **`print_host`** in the machine preset is a placeholder
  (`PRINTER.LAN.ADDRESS`) - set it to the container's LAN address.
- The **RP2040 serial** in `config/printer.cfg` and the udev rule
  (`usb-Klipper_rp2040_...`) is unique to this board. Find yours with
  `ls /dev/serial/by-id/`.
