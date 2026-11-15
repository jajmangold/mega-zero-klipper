# Calibration

How each measured value was obtained, and in what order. The order matters —
several of these invalidate the ones after them.

## Order of operations

1. **Axis travel limits** — everything downstream is meaningless if positions
   are fiction
2. **Probe offsets** — measure with a ruler
3. **`rotation_distance`** (flow)
4. **`z_tilt`** (gantry level)
5. **Bed mesh**
6. **`z_offset`** — must come *after* flow and levelling
7. **Pressure advance**

---

## 1. Axis travel

**X travel is 185 mm**, despite a 220 mm bed. `position_max` was 220, and every
move beyond 185 drove the carriage into the frame and lost steps silently.

Measure by jogging in small steps and watching/listening, then set
`position_max` so Klipper *refuses* the move rather than attempting it.

> **Y is still unverified** at `position_max: 220`. Same condition that caused
> the X crashes. Worth measuring before anything uses the back of the bed.

## 2. Probe offsets

**Measure with a ruler: nozzle tip to the centre of the probe face.**

Attempts to infer these from where the probe stops triggering produced numbers
that were simply wrong — bed tilt and a loaded mesh both move the apparent
"edge" by millimetres. The ruler took ten seconds and landed within 5 mm of the
config's existing values.

```
x_offset: -55.0
y_offset: -19.0
```

**Bed-slinger sign trap:** the probe sits physically *behind* the nozzle but is
at a *lower* bed Y — it leaves the plate's front edge before the nozzle does, so
`y_offset` is **negative**. Physical "behind" and bed-coordinate "+Y" are
opposite on a moving-bed machine.

**Consequence:** with `x_offset -55` and 185 mm of X travel, the probe can only
reach **bed X 0–130**. The right ~55 mm of the plate is permanently
unmeasurable. Keep parts within X 15–130 for properly-meshed first layers.

## 3. `rotation_distance` — measure it

**A swapped extruder means this is unknown, not approximately right.**

1. Mark the filament a known distance from the extruder inlet
2. Heat to printing temperature, `M83`, command a known extrusion
3. Measure what remains

```
new = old × (actual fed ÷ commanded)
```

Command *less* than the mark distance so the mark stays visible — if it
disappears into the extruder all you learn is "at least that much".

Worked example from this machine:

| step | commanded | fed | result |
|---|---|---|---|
| start | — | — | 8.312 (old geared bowden extruder) |
| 1 | 50 | 125 | → 20.78 |
| 2 | 50 | 55 | → 22.86 |
| final | — | — | **22.2** (trimmed ~3% by eye) |

**Sanity check the result against the hardware:** `22.2 / π ≈ 7.07 mm`, a
standard MK8 hobbed gear. If the number doesn't divide by π into a believable
drive-gear diameter, it's wrong.

**Symptoms of getting this wrong:** extruder skipping (being asked for more than
the nozzle can melt), and a 20 mm cube measuring tall in **Z only** — X and Y
stay near 20.3 because surplus material has nowhere to go but up.

## 4. `z_tilt` — dual Z

Took the bed from **1.42 mm to 0.30 mm** range in one pass.

```
z_positions:          # screw positions, ~438 mm apart
    -109, 85          # 396 mm frame + one NEMA 17 body
    329, 85
points:               # probe points - both left of centre because
    20, 120           # x_offset -55 caps the probe at bed X~130
    115, 120
```

Leverage ratio is 438 ÷ 95 ≈ **4.6**, so every 0.1 mm measured at the probe
becomes ~0.46 mm of screw movement. Approximate screw positions are fine (it
iterates) but not arbitrary.

### When it oscillates instead of converging

Later runs stopped converging and Klipper aborted with *Retries aborting: Probed
points range is increasing*:

```
0.9975 → 0.2275 → 0.3725 → 0.2200 → 0.3700 → 0.3850
```

One pass removes the gross error, then it flips between two states forever.
That is overshoot with spring-back, and the cause here was **cables dragging on
the gantry** — the load changes as X travels between the two probe points, so
the tilt is real when measured and gone once corrected.

**Rule out the sensor first; it takes a minute.** Both of these came back clean,
which is what proved the fault was mechanical:

```
PROBE_ACCURACY SAMPLES=10        # within a run:   0.002 mm, stdev 0.0015
G28 then probe one point, ×4     # across homings: 0.0025 mm
```

Then confirm the second motor actually turns its screw, comparing the **tilt**
(the difference between the two points) before and after — that is independent
of where homing put zero:

```
FORCE_MOVE STEPPER=stepper_z1 DISTANCE=2.0 VELOCITY=1
# expect the tilt to change by 2.0 × 95/438 = 0.434 mm
```

Measured 0.388 mm at 10 mm/s and 0.474 mm at 1 mm/s — it tracks at both speeds,
so neither a stall nor a slipping coupler.

> **Restore every `FORCE_MOVE` in the same breath.** One unpaired +2 mm left the
> gantry racked and silently poisoned the next three measurements, which looked
> exactly like the Z geometry drifting between homings.

**Settle for what the mesh can absorb.** With `x_offset -55` the probe reaches
only bed X 0–130, so `z_tilt` extrapolates from two points 95 mm apart out to
screws 438 mm apart — a **4.6× amplification** of any flex. Chasing 0.05 mm is
not achievable here:

```
Z_TILT_ADJUST RETRIES=3 RETRY_TOLERANCE=0.25
```

That strips the gross error in one pass and leaves ~0.24 mm for the mesh. Take
the mesh **after** it, and keep `PRINT_START` loading the saved profile without
re-running `z_tilt` — otherwise the gantry lands in a different state than the
mesh was measured in.

## 5. Bed mesh

5×5 over X 15–120, Y 45–195. Residual range **0.467 mm**, which reads as a
~0.3 mm left-to-right ramp (the `z_tilt` residual above) sitting on a ~0.2 mm
front-to-back dish:

```
          X=15   X=41   X=67   X=94   X=120
Y=45    -0.412 -0.327 -0.299 -0.264 -0.047
Y=82    -0.234 -0.152 -0.107 -0.057 +0.006
Y=120   -0.232 -0.134 -0.079 -0.019 +0.031
Y=157   -0.324 -0.234 -0.179 -0.117 -0.039
Y=195   -0.437 -0.332 -0.267 -0.189 -0.129
```

`fade_start 1.0` / `fade_end 10.0` is important: without it the bed-shape
correction applies at *every* layer, so a tall part is still being Z-shifted by
the plate's shape at its top, and any out-of-mesh extrapolation compounds all
the way up instead of dying out.

## 6. `z_offset`

**Must be done after flow is correct.** A `z_offset` measured while
over-extruding is worthless: the fat bead fills a gap that is really too large.

Paper feel has misled this machine repeatedly — ooze on the tip drags the paper
early by roughly the amount being measured. Retract first and wipe the nozzle.
[`tools/zladder.py`](../tools/zladder.py) draws real extruded lines at known Z
instead, which is the honest instrument.

Sign: lines **dig in** → nozzle closer than Klipper thinks → `z_offset` too
large, reduce. Lines sit as **round beads** → increase. Too small is the safe
direction to be wrong (prints in the air); too large drives the nozzle into the
plate.

**A hotend or extruder swap invalidates this value outright.** `z_offset` *is*
the nozzle-to-probe vertical relationship, so changing the heater block, the
nozzle or the whole extruder makes the stored number fiction. Re-run
`PROBE_CALIBRATE` rather than nudging it — after the direct-drive conversion the
error was **0.232 mm**, and an evening of 0.05 steps never covered it.

**Read the number Klipper computes, not the gcode Z you stopped at.** `ACCEPT`
evaluates `new = probe_trigger_Z − nozzle_touch_Z`, both measured at the *same*
XY, which is why it is the trustworthy figure. Stopping at Z −0.650 gave 1.637,
not 1.405 + 0.650 — the trigger height at that point was 0.987, not the old
offset.

> **`[idle_timeout]` aborts a manual probe and drops the steppers.**
> Mid-paper-test `TESTZ` then fails with *Unknown command: "TESTZ"* and
> `homed_axes` reads empty. Run `SET_IDLE_TIMEOUT TIMEOUT=3600` first.

Current: **1.637**

## 7. Pressure advance

`0.04`, and **it barely matters on this machine**. A full 0 → 0.100 sweep showed
no visible difference anywhere, because at `max_accel: 500` there is almost no
pressure lag for PA to correct. Don't spend time here unless acceleration is
raised — and raising it without an input shaper brings ringing.

[`tools/gen_pa_dd.py`](../tools/gen_pa_dd.py) generates the sweep tower.
Read it with **calipers from the bed**, not by counting layers.
