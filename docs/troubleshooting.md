# Troubleshooting

Faults that have actually happened on this machine, with the symptom that led to
them. Several of these cost hours because the symptom pointed somewhere else.

---

## "The probe is dead" — it almost certainly isn't

**Symptom:** `No trigger on probe after full movement`, then the probe reads
`open` at every height, even directly over the plate at 0.6 mm. Looks
conclusively like a failed sensor or a broken wire.

**Cause:** a crash past the X travel limit (185 mm) lost steps, so the reported
position is fiction and the probe is nowhere near where you think. Worse, each
failed `PROBE` drives Z down the full travel looking for a trigger, pushing the
nozzle into the bed and corrupting the Z reference as well.

**Fix:** re-home, then re-measure. Do not start pulling wires.

**Prevention:** `position_max: 185` on X. It was 220, which is what allowed the
crash in the first place.

---

## Probe triggers in one place but not another

**Symptom:** the probe works at bed centre but reads `open` elsewhere, and the
same point reads differently on two passes.

**Cause:** testing too close to the trigger threshold. With `z_offset ≈ 1.3`,
sweeping at Z = 1.2 is marginal — on the low side of a tilted bed the probe
never gets in range, which looks like "the plate ends here".

**Fix:** sweep at **Z 0.6 or lower**, with a known-good Z reference, and
`BED_MESH_CLEAR` first. A loaded mesh changes the real Z as you move, and
outside the meshed area Klipper *extrapolates* — it was applying −0.6 mm at
X=20 in one case.

---

## Prints degrade with height / blobby chaos

Check these in order. Several can look identical.

**1. Slicer acceleration overrides.** Orca's Klipper flavour emits
`SET_VELOCITY_LIMIT ACCEL=` which **overrides `max_accel` at runtime**. Stock
profiles ask for 5000–7000 mm/s² — this machine does 500 and has no input
shaper.

```bash
grep -o 'ACCEL=[0-9]*' file.gcode | sort | uniq -c
```

**2. `rotation_distance` wrong.** Especially after an extruder swap. Measure it
(see [calibration.md](calibration.md)); do not assume. Over-extrusion makes the
extruder skip and makes a 20 mm cube come out 21 mm tall in Z.

**3. Heat creep.** The heatbreak fan is on **FAN4, an unswitched 12 V
passthrough with no MOSFET**, so there is no `[heater_fan]` section and
**Klipper cannot tell you it has stopped**. Eyeball it.

**4. Tree supports in PETG.** Branches are thin and unbraced, PETG is sticky
rather than brittle, and the nozzle drags the tips around. Use normal/grid.

---

## The decisive diagnostic

**If hand-generated gcode prints perfectly and sliced files fail, the machine is
not the variable — diff the gcode.**

The generators in [`tools/`](../tools/) emit no `SET_VELOCITY_LIMIT` and no
slicer-specific commands. If those come out clean and Orca's don't, the fault is
in the slicer output. This single comparison would have saved hours.

---

## RP2040 comes back in a shutdown state

**Symptom:** after a host restart or `FIRMWARE_RESTART`,
`Can not update MCU 'pico' config as it is shutdown`, and only one of two MCUs
configures.

**Cause:** the RP2040 is USB-powered, so it never resets when klippy restarts —
it holds its previous shutdown state.

**Fix:** `FIRMWARE_RESTART` → **wait ~25 s** → `systemctl restart klipper`. The
wait matters: resetting the pico makes it re-enumerate, which drops its device
mapping, so restarting klippy too early just fails again. A plain service
restart alone never works.

The udev rule in [`container/`](../container/) automates this.

---

## First layer wrong after a flow change

`z_offset` measured while over-extruding is worthless — a fat bead fills a gap
that is actually too large, hiding a nozzle that is too high. **Fix flow first,
then `z_offset`.** Never the other way round.

---

## Z_TILT_ADJUST never converges

`Too many retries`, or `Retries aborting: Probed points range is increasing`.

Check in this order — the first two are cheap and clear the sensor:

1. **`PROBE_ACCURACY SAMPLES=10`** — should be ~0.002 mm here
2. **`G28` + probe one point, four times** — should be ~0.0025 mm here
3. **`FORCE_MOVE STEPPER=stepper_z1 DISTANCE=2.0 VELOCITY=1`** and watch the
   *tilt* change, not absolute Z. Expect 2.0 × 95/438 = 0.434 mm
4. **Cables dragging on the gantry** — the cause on this machine. The load
   varies as X moves between the probe points, so the tilt is genuine when
   measured and absent once corrected. Oscillation between two values is the
   signature
5. **Any unpaired `FORCE_MOVE`** left in the machine from earlier testing

A measured range that *plateaus or oscillates* while the probe repeats to
0.002 mm is mechanical, never the sensor. Given `x_offset -55` limits the probe
to bed X 0–130, 0.05 mm is not reachable on this machine — use
`RETRY_TOLERANCE=0.25` and let the mesh carry the rest.

---

## A paper test dies halfway through

`TESTZ` returns `Unknown command: "TESTZ"` and `toolhead.homed_axes` is empty.

`[idle_timeout]` fired while you were getting the paper in, which aborts the
manual probe **and** drops the steppers, so the position is gone too. Always:

```
SET_IDLE_TIMEOUT TIMEOUT=3600
```

Re-home and restart `PROBE_CALIBRATE` from the beginning afterwards.

---

## Reading probe results over the Moonraker API

`probe/last_z_result` did **not** refresh between two consecutive `PROBE`s —
both points returned byte-identical values, which read as a perfectly level bed
and sent the diagnosis down the wrong path for several rounds.

Use `PROBE_ACCURACY` and parse `average` out of `klippy.log` instead. Plain
`PROBE` does not write its `probe at X,Y is z=` line to the log at all; that
line only appears on the console.

**Sanity-check any two readings that come back exactly equal.** On this bed that
is physically impossible.

---

## Config file traps

**Nothing goes below the `#*# <--- SAVE_CONFIG --->` marker.** Appending macros
there makes Klipper stop reading the autosaved values — `z_offset` then errors
as "must be specified" while sitting visibly in the file.

**`[display_status]` must not be declared** if `[display]` is present; it is
provided implicitly and declaring both is a config error.

**Guard retracts in park macros** with `{% if printer.extruder.can_extrude %}`.
`CANCEL_PRINT` runs `TURN_OFF_HEATERS` first, so an unguarded `G1 E-1` fails
with *Extrude below minimum temp* and leaves the print stuck in `PAUSED`.

---

## Orca preset traps

**Orca silently reverts preset edits made while it is running.** It writes
presets back from its in-memory copy on exit. Close Orca before editing files
under `user/default/`. The same acceleration setting was reverted three times
before this was spotted.

**Hand-written presets need the variant arrays.** A preset missing
`print_extruder_variant` / `filament_extruder_variant` is rejected **silently** —
it simply never appears in the dropdown. Values must also match the variant
count (e.g. six temperature entries, not one).

The reliable route is to duplicate an existing preset *in the UI*, then edit
that file. Orca authors it correctly; you only change values.

**Find a valid `inherits` name** by slicing anything and reading
`printer_settings_id` / `filament_settings_id` / `print_settings_id` from the
gcode footer.
